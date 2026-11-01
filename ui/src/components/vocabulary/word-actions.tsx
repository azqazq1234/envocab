import { Pencil, Trash2 } from "lucide-react";
import { IconButton } from "@/components/ui/icon-button";

export function WordActions({
  term,
  onEdit,
  onDelete,
}: {
  term: string;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="flex items-center gap-1">
      <IconButton
        className="text-emerald-700 hover:text-emerald-800"
        aria-label={`Edit ${term}`}
        title="Edit"
        onClick={onEdit}
      >
        <Pencil aria-hidden="true" className="size-4" />
      </IconButton>
      <IconButton
        className="text-red-600 hover:text-red-700"
        aria-label={`Delete ${term}`}
        title="Delete"
        onClick={onDelete}
      >
        <Trash2 aria-hidden="true" className="size-4" />
      </IconButton>
    </div>
  );
}
