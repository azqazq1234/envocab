import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export function IconButton({
  className,
  size = "icon",
  type = "button",
  ...props
}: Omit<ComponentProps<typeof Button>, "variant">) {
  return (
    <Button
      {...props}
      type={type}
      variant="ghost"
      size={size}
      className={cn(
        "cursor-pointer bg-transparent hover:bg-transparent aria-expanded:bg-transparent dark:hover:bg-transparent dark:aria-expanded:bg-transparent",
        className,
      )}
    />
  );
}
