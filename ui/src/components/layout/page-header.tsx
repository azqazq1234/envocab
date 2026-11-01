import type { ReactNode } from "react";

export function PageHeader({
  title,
  titleId,
  children,
}: {
  title: string;
  titleId?: string;
  children?: ReactNode;
}) {
  return (
    <div className="relative flex shrink-0 flex-wrap items-center gap-x-4 gap-y-3 p-3 @[1100px]:grid @[1100px]:h-14 @[1100px]:grid-cols-[10%_10%_10%_10%_20%] @[1100px]:gap-0 @[1100px]:p-0">
      <h1
        id={titleId}
        title={title}
        className="order-1 min-w-0 max-w-full text-lg font-semibold tracking-tight text-emerald-700 [overflow-wrap:anywhere] @[1100px]:h-full @[1100px]:max-w-none @[1100px]:pt-3.5 @[1100px]:pl-3.5 @[1100px]:whitespace-nowrap"
      >
        {title}
      </h1>
      {children}
    </div>
  );
}
