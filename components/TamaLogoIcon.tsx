export function TamaLogoIcon({ className = "h-11 w-11" }: { className?: string }) {
  return (
    <svg viewBox="0 0 84 84" className={className} fill="none" aria-hidden="true">
      <rect x="8" y="8" width="68" height="68" rx="18" fill="#FACC15" stroke="#1E293B" strokeWidth="3" />
      <rect x="18" y="18" width="48" height="34" rx="8" fill="#DCFCE7" stroke="#1E293B" strokeWidth="3" />
      <circle cx="33" cy="31" r="4" fill="#1E293B" />
      <circle cx="51" cy="31" r="4" fill="#1E293B" />
      <path d="M32 41C35.5 45 48.5 45 52 41" stroke="#15803D" strokeWidth="3" strokeLinecap="round" />
      <path d="M40 4H44V12H40z" fill="#1E293B" />
      <circle cx="42" cy="4" r="4" fill="#FEF3C7" stroke="#1E293B" strokeWidth="3" />
      <circle cx="27" cy="61" r="5" fill="#22C55E" stroke="#1E293B" strokeWidth="3" />
      <circle cx="42" cy="65" r="5" fill="#F97316" stroke="#1E293B" strokeWidth="3" />
      <circle cx="57" cy="61" r="5" fill="#38BDF8" stroke="#1E293B" strokeWidth="3" />
    </svg>
  );
}
