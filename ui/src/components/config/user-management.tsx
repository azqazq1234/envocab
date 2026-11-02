"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { apiRequest } from "@/lib/vocabulary-api";
import type { User } from "@/components/auth/auth-provider";
import { useAsyncSubmit } from "@/hooks/use-async-submit";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { IconButton } from "@/components/ui/icon-button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from "@/components/ui/table";

type ManagedUser = User & { created_at: string; studied: number };
type UserPage = { items: ManagedUser[]; total: number; page: number; total_pages: number };
type Action = { mode: "create" } | { mode: "edit" | "delete"; user: ManagedUser };

function UserActionDialog({ action, onClose, onSaved }: {
  action: Action;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [username, setUsername] = useState(action.mode === "create" ? "" : action.user.username);
  const { busy, error, run } = useAsyncSubmit("Unable to save user.");
  const deleting = action.mode === "delete";

  function submit(event: FormEvent) {
    event.preventDefault();
    void run(async (signal) => {
      const path = action.mode === "create" ? "/admin/users" : `/admin/users/${action.user.id}`;
      await apiRequest(path, {
        method: deleting ? "DELETE" : action.mode === "create" ? "POST" : "PATCH",
        signal,
        ...(deleting ? {} : { headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username }) }),
      });
      if (!signal.aborted) { onSaved(); onClose(); }
    });
  }

  return (
    <Dialog open onOpenChange={(open) => { if (!open && !busy) onClose(); }}>
      <DialogContent showCloseButton={!busy}>
        <DialogTitle>{deleting ? "Delete user?" : action.mode === "create" ? "Add user" : "Edit user"}</DialogTitle>
        <DialogDescription>
          {deleting ? `Permanently delete ${action.user.username} and all their learning data? All sessions will be signed out. This cannot be undone.` : "Usernames contain 1–40 letters, numbers, underscores or hyphens."}
        </DialogDescription>
        <form onSubmit={submit} className="grid gap-4">
          {!deleting ? (
            <div className="grid gap-2">
              <label htmlFor="managed-username" className="text-sm font-medium">Username</label>
              <Input id="managed-username" autoComplete="off" value={username} onChange={(event) => setUsername(event.target.value)} required maxLength={40} disabled={busy} />
            </div>
          ) : null}
          {error ? <p role="alert" className="text-sm text-red-700">{error}</p> : null}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={busy} className="cursor-pointer">Cancel</Button>
            <Button type="submit" disabled={busy} className={`cursor-pointer text-white ${deleting ? "bg-red-600 hover:bg-red-700" : "bg-emerald-700 hover:bg-emerald-800"}`}>
              {busy ? "Please wait…" : deleting ? "Delete user" : "Save"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function UserManagement() {
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const [action, setAction] = useState<Action | null>(null);
  const [result, setResult] = useState<{ key: string; data?: UserPage; error?: string } | null>(null);
  const key = JSON.stringify([query, page, revision]);
  const loading = result?.key !== key;
  const data = loading ? undefined : result?.data;

  useEffect(() => {
    const request = new AbortController();
    const params = new URLSearchParams({ q: query, page: String(page) });
    apiRequest<UserPage>(`/admin/users?${params}`, { signal: request.signal, cache: "no-store" })
      .then((data) => { if (!request.signal.aborted) setResult({ key, data }); })
      .catch((cause: unknown) => {
        if (!request.signal.aborted) setResult({ key, error: cause instanceof Error ? cause.message : "Unable to load users." });
      });
    return () => request.abort();
  }, [key, query, page]);

  return (
    <section aria-labelledby="users-title">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <h1 id="users-title" className="text-2xl font-semibold text-emerald-800">Users</h1>
        <Button onClick={() => setAction({ mode: "create" })} className="cursor-pointer bg-emerald-700 text-white hover:bg-emerald-800"><Plus aria-hidden="true" className="size-4" />Add user</Button>
      </div>
      <form onSubmit={(event) => { event.preventDefault(); setQuery(search.trim()); setPage(1); }} className="mb-5 flex gap-2">
        <Input aria-label="Search users" placeholder="Search username" value={search} onChange={(event) => setSearch(event.target.value)} maxLength={100} className="max-w-sm bg-white" />
        <Button type="submit" variant="outline" className="cursor-pointer">Search</Button>
      </form>
      <div className="overflow-hidden rounded-xl bg-white p-2 shadow-sm" aria-busy={loading}>
        <Table aria-label="User management">
          <TableHeader><TableRow>
            <TableHead>ID</TableHead><TableHead>Username</TableHead><TableHead>Role</TableHead><TableHead>Studied</TableHead><TableHead>Created</TableHead><TableHead>Actions</TableHead>
          </TableRow></TableHeader>
          <TableBody>
            {data?.items.map((user) => (
              <TableRow key={user.id}>
                <TableCell className="text-stone-500">{user.id}</TableCell>
                <TableCell className="font-medium">{user.username}</TableCell>
                <TableCell>{user.is_admin ? "Administrator" : "User"}</TableCell>
                <TableCell>{user.studied}</TableCell>
                <TableCell className="text-stone-500">{new Date(user.created_at).toLocaleDateString("en-CA")}</TableCell>
                <TableCell>
                  {!user.is_admin ? <div className="flex gap-1">
                    <IconButton aria-label={`Edit ${user.username}`} onClick={() => setAction({ mode: "edit", user })} className="text-emerald-700"><Pencil aria-hidden="true" className="size-4" /></IconButton>
                    <IconButton aria-label={`Delete ${user.username}`} onClick={() => setAction({ mode: "delete", user })} className="text-red-600"><Trash2 aria-hidden="true" className="size-4" /></IconButton>
                  </div> : <span className="text-xs text-stone-400">Protected</span>}
                </TableCell>
              </TableRow>
            ))}
            {!data?.items.length ? <TableRow><TableCell colSpan={6} className="h-32 text-center text-stone-500">
              {loading ? <span role="status">Loading…</span> : result?.error ? <div role="alert">{result.error}<Button variant="link" onClick={() => setRevision((value) => value + 1)} className="cursor-pointer">Retry</Button></div> : "No users found."}
            </TableCell></TableRow> : null}
          </TableBody>
        </Table>
      </div>
      <div className="mt-4 flex items-center justify-between gap-3 text-sm text-stone-500">
        <span>{data ? `${data.total} users` : "—"}</span>
        <div className="flex items-center gap-3">
          <Button variant="outline" disabled={loading || !data || data.page <= 1} onClick={() => setPage((data?.page ?? 1) - 1)} className="cursor-pointer">Previous</Button>
          <span>{data ? `${data.page} / ${data.total_pages}` : "—"}</span>
          <Button variant="outline" disabled={loading || !data || data.page >= data.total_pages} onClick={() => setPage((data?.page ?? 1) + 1)} className="cursor-pointer">Next</Button>
        </div>
      </div>
      {action ? <UserActionDialog action={action} onClose={() => setAction(null)} onSaved={() => setRevision((value) => value + 1)} /> : null}
    </section>
  );
}
