import { AccountMenu } from "@/components/auth/account-menu";
import { MobileNavigation } from "@/components/layout/mobile-navigation";
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
      <div className="order-1 flex w-full items-center gap-3 sm:contents">
        <div className="shrink-0 sm:hidden"><MobileNavigation /></div>
        <h1
          id={titleId}
          title={title}
          className="min-w-0 max-w-full sm:order-1 text-lg font-semibold tracking-tight text-emerald-700 [overflow-wrap:anywhere] @[1100px]:h-full @[1100px]:max-w-none @[1100px]:pt-3.5 @[1100px]:pl-3.5 @[1100px]:whitespace-nowrap"
        >
          {title}
        </h1>
        <div className="ml-auto shrink-0 [&>div]:pr-0 sm:hidden"><AccountMenu /></div>
      </div>
      {children}
    </div>
  );
}
