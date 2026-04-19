"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { startTamagotchiBgm, resumeTamagotchiBgm } from "@/lib/tamagotchiBgm";

export function BgmProvider() {
  const pathname = usePathname();

  useEffect(() => {
    const stop = startTamagotchiBgm();
    const unlock = () => resumeTamagotchiBgm();
    window.addEventListener("pointerdown", unlock);
    return () => {
      window.removeEventListener("pointerdown", unlock);
      stop();
    };
  }, [pathname]);

  return null;
}
