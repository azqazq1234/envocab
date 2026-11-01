import { PageHeader } from "@/components/layout/page-header";
import { GroupProgressCards } from "@/components/dashboard/group-progress-cards";

export default function DashboardPage() {
  return (
    <div className="@container/dashboard bg-[#fcfcfc]">
      <div className="flex min-h-[calc(100dvh-3.5rem)] flex-col @[992px]/dashboard:h-[calc(100dvh-3.5rem)] @[992px]/dashboard:min-h-0 @[992px]/dashboard:overflow-hidden">
        <PageHeader title="Dashboard" />
        <GroupProgressCards />
      </div>
    </div>
  );
}
