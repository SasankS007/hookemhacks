import { spawn } from "node:child_process";
import { createServer } from "node:net";

/** @param {number} port */
function portAvailable(port) {
  return new Promise((resolve) => {
    const s = createServer();
    s.once("error", () => resolve(false));
    s.listen(port, "0.0.0.0", () => {
      s.close(() => resolve(true));
    });
  });
}

async function resolveBackendPort() {
  if (process.env.BACKEND_PORT) {
    const p = parseInt(process.env.BACKEND_PORT, 10);
    if (!Number.isFinite(p)) {
      throw new Error("BACKEND_PORT must be a number");
    }
    if (!(await portAvailable(p))) {
      throw new Error(
        `Port ${p} is already in use (BACKEND_PORT). Stop the other process or use a different BACKEND_PORT.`,
      );
    }
    return p;
  }
  for (let p = 8000; p < 8020; p++) {
    if (await portAvailable(p)) {
      return p;
    }
  }
  throw new Error("No free TCP port in range 8000–8019 for the FastAPI backend.");
}

const children = [];
let shuttingDown = false;

function run(name, command, args, options = {}) {
  const child = spawn(command, args, {
    stdio: "inherit",
    shell: false,
    ...options,
  });

  child.on("exit", (code, signal) => {
    if (shuttingDown) {
      return;
    }

    shuttingDown = true;
    for (const proc of children) {
      if (proc !== child && !proc.killed) {
        proc.kill("SIGTERM");
      }
    }

    if (signal) {
      process.kill(process.pid, signal);
      return;
    }

    process.exit(code ?? 0);
  });

  children.push(child);
  return child;
}

async function main() {
  const backendPort = await resolveBackendPort();
  // Must match the bound port so Next rewrites hit this uvicorn (overrides stale BACKEND_URL in env).
  const backendUrl = `http://localhost:${backendPort}`;

  if (backendPort !== 8000) {
    console.log(`[dev] Port 8000 busy — using backend ${backendUrl}`);
  } else {
    console.log(`[dev] Backend API → ${backendUrl}`);
  }

  run("backend", "python3", ["-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", String(backendPort)], {
    cwd: new URL("../backend/", import.meta.url),
  });

  run("frontend", "npm", ["run", "dev:frontend"], {
    cwd: new URL("../", import.meta.url),
    env: { ...process.env, BACKEND_URL: backendUrl },
  });

  for (const signal of ["SIGINT", "SIGTERM"]) {
    process.on(signal, () => {
      if (shuttingDown) {
        return;
      }
      shuttingDown = true;
      for (const child of children) {
        if (!child.killed) {
          child.kill("SIGTERM");
        }
      }
      process.exit(0);
    });
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
