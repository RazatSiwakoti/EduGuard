import { useEffect, useState } from "react";
import { getInitials } from "../utils/userDisplay";

interface AvatarProps {
  src: string | null;
  name: string;
  size: "sm" | "md" | "lg" | "xl";
  className?: string;
}

const SIZE_CLASSES: Record<AvatarProps["size"], string> = {
  sm: "h-7 w-7 text-xs",
  md: "h-8 w-8 text-xs",
  lg: "h-12 w-12 text-sm",
  xl: "h-24 w-24 text-2xl",
};

export default function Avatar({ src, name, size, className = "" }: AvatarProps) {
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    setImageFailed(false);
  }, [src]);

  return (
    <span className={`inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-stone-800 font-semibold text-white ${SIZE_CLASSES[size]} ${className}`} aria-label={name}>
      {src && !imageFailed ? (
        <img src={src} alt="" className="h-full w-full object-cover" onError={() => setImageFailed(true)} />
      ) : (
        getInitials(name)
      )}
    </span>
  );
}
