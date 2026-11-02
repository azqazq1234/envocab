"use client";

import { useState } from "react";
import { LogOut, Trash2 } from "lucide-react";
import { useAuth } from "./auth-provider";
import { useAsyncSubmit } from "@/hooks/use-async-submit";
import { Menu } from "@base-ui/react/menu";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";

const avatarClassName = "flex size-9 cursor-pointer items-center justify-center rounded-full bg-emerald-100 text-sm font-semibold text-emerald-800 ring-1 ring-emerald-700/10 hover:bg-emerald-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700 disabled:opacity-50";

export function AccountMenu() {
  const { user, logout, deleteAccount } = useAuth();
  const [open, setOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const { busy, error, setError, run } = useAsyncSubmit("Unable to update account.");

  if (!user) return null;

  return (
    <div className="ml-auto pr-4">
      <Menu.Root open={open} onOpenChange={(value) => { if (!busy) { setOpen(value); setError(""); } }}>
        <Menu.Trigger
          aria-label={`Account: ${user.username}`}
          className={avatarClassName}
        >
          {user.username.slice(0, 2).toUpperCase()}
        </Menu.Trigger>
        <Menu.Portal>
          <Menu.Positioner align="end" sideOffset={8} className="z-50">
            <Menu.Popup aria-label="Account menu" className="w-44 max-w-[calc(100vw-2rem)] rounded-xl bg-white p-1.5 text-sm text-stone-900 shadow-[0_2px_4px_rgb(0_0_0/0.06),0_8px_24px_rgb(0_0_0/0.12)] outline-none">
              <div className="px-3 pt-2.5 pb-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="min-w-0 truncate font-medium">{user.username}</p>
                  {!user.is_admin ? <Menu.Item
                    aria-label={`Delete account ${user.username}`}
                    disabled={busy}
                    onClick={() => { setError(""); setConfirmDelete(true); }}
                    className="flex size-7 shrink-0 cursor-pointer items-center justify-center rounded-md text-red-600 outline-none data-highlighted:bg-red-50 data-disabled:opacity-50"
                  >
                    <Trash2 aria-hidden="true" className="size-4" />
                  </Menu.Item> : null}
                </div>
                <p className="mt-1 flex items-center gap-1 text-xs text-stone-500">
                  {user.is_admin ? "Administrator" : "User"}
                </p>
              </div>
              <Menu.Separator className="mx-1 mb-1 h-px bg-stone-100" />
              {error && !confirmDelete ? <p role="alert" className="px-3 py-2 text-xs text-red-700">{error}</p> : null}
              <Menu.Item
                closeOnClick={false}
                disabled={busy}
                onClick={() => void run(logout)}
                className="flex min-h-10 cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-emerald-800 outline-none data-highlighted:bg-emerald-50 data-disabled:cursor-wait data-disabled:opacity-50"
              >
                <LogOut aria-hidden="true" className="size-4" />
                {busy ? "Logging out…" : "Log out"}
              </Menu.Item>
            </Menu.Popup>
          </Menu.Positioner>
        </Menu.Portal>
      </Menu.Root>
      <Dialog open={!user.is_admin && confirmDelete} onOpenChange={(value) => { if (!busy) setConfirmDelete(value); }}>
        <DialogContent showCloseButton={!busy}>
          <DialogTitle>Delete account?</DialogTitle>
          <DialogDescription className="leading-6">
            Permanently delete <strong className="break-all font-semibold text-stone-900">{user.username}</strong>?
            All learning progress and account data will be erased, and all sessions will be signed out.
            This cannot be undone.
          </DialogDescription>
          {error ? <p role="alert" className="text-sm text-red-700">{error}</p> : null}
          <div className="mt-2 flex justify-end gap-2">
            <Button type="button" variant="outline" disabled={busy} onClick={() => setConfirmDelete(false)} className="cursor-pointer">Cancel</Button>
            <Button type="button" disabled={busy} onClick={() => void run(deleteAccount)} className="cursor-pointer bg-red-600 text-white hover:bg-red-700">
              {busy ? "Deleting…" : "Delete account"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
