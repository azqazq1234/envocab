import type { WordMeaning } from "@/lib/vocabulary-api";
import { partOfSpeechLabels } from "@/lib/parts-of-speech";

export function WordMeanings({
  meanings,
  inline = false,
}: {
  meanings: WordMeaning[];
  inline?: boolean;
}) {
  return meanings.map((meaning, index) => (
    <span key={index}>
      {inline && index > 0 ? (
        <span className="mx-3 text-stone-300">·</span>
      ) : null}
      {meaning.part_of_speech ? (
        <span
          className={`mr-2 font-bold text-emerald-700 ${inline ? "text-xs" : ""}`}
          title={meaning.part_of_speech}
        >
          {partOfSpeechLabels[meaning.part_of_speech] ?? meaning.part_of_speech}
        </span>
      ) : null}
      <span lang="zh-CN">{meaning.meaning}</span>
    </span>
  ));
}
