export const vocabularyGroups = [
  {
    slug: "all",
    label: "All",
    abbreviation: "ALL",
  },
  {
    slug: "junior",
    label: "Junior",
    abbreviation: "J",
  },
  {
    slug: "senior",
    label: "Senior",
    abbreviation: "S",
  },
  {
    slug: "cet4",
    label: "CET-4",
    abbreviation: "4",
  },
  {
    slug: "cet6",
    label: "CET-6",
    abbreviation: "6",
  },
  {
    slug: "postgraduate",
    label: "Postgraduate",
    abbreviation: "P",
  },
  {
    slug: "ielts",
    label: "IELTS",
    abbreviation: "I",
  },
  {
    slug: "coca",
    label: "COCA",
    abbreviation: "C",
  },
] as const;

export const learningGroups = vocabularyGroups.filter(
  (group) => group.slug !== "all",
);

export const seniorTypes = [
  { slug: "core", label: "core" },
  { slug: "extend", label: "extend" },
  { slug: "basic", label: "basic" },
] as const;

export const groupAbbreviations: Record<string, string> = Object.fromEntries(
  vocabularyGroups.map((group) => [group.slug, group.abbreviation]),
);
