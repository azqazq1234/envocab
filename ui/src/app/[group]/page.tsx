import { notFound } from "next/navigation";
import { vocabularyGroups } from "@/lib/vocabulary-groups";
import { VocabularyTabs } from "@/components/vocabulary/vocabulary-tabs";

export function generateStaticParams() {
  return vocabularyGroups.map((group) => ({ group: group.slug }));
}

export default async function GroupPage({
  params,
}: {
  params: Promise<{ group: string }>;
}) {
  const { group: slug } = await params;
  const group = vocabularyGroups.find((item) => item.slug === slug);
  if (!group) notFound();
  return (
    <section
      aria-labelledby="vocabulary-title"
      className="h-[calc(100dvh-3.5rem)] min-h-0 min-w-0 bg-[#fcfcfc]"
    >
      <VocabularyTabs
        key={group.slug}
        groupLabel={group.label}
        groupSlug={group.slug}
      />
    </section>
  );
}
