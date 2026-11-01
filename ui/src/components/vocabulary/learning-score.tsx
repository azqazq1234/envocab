import {
  LEARNING_SCORE_COLORS,
  MAX_LEARNING_SCORE,
} from "@/lib/learning-colors";

export function LearningScore({ score }: { score: number }) {
  const level = Math.max(0, Math.min(MAX_LEARNING_SCORE, Math.floor(score)));
  return (
    <svg
      viewBox="0 0 40 40"
      className="size-6 shrink-0"
      role="img"
      aria-label={`Learning score: ${level} of ${MAX_LEARNING_SCORE}`}
    >
      {level > 0 ? (
        <circle
          cx="20"
          cy="20"
          r="15"
          fill="none"
          stroke={LEARNING_SCORE_COLORS[level - 1]}
          strokeWidth="5"
          pathLength="100"
          strokeDasharray={`${(level / MAX_LEARNING_SCORE) * 100} 100`}
          transform="rotate(-90 20 20)"
        />
      ) : null}
    </svg>
  );
}
