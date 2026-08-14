"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useState } from "react";

import { apiRequest } from "@/lib/api";
import type {
  Notification,
  NotificationLevel,
  NotificationUnreadCount,
} from "@/types";

export default function NotificationCenter() {
  const queryClient = useQueryClient();
  const [isOpen, setIsOpen] = useState(false);

  const countQuery = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () =>
      apiRequest<NotificationUnreadCount>(
        "/notifications/unread-count",
      ),
    refetchInterval: 30_000,
  });

  const notificationsQuery = useQuery({
    queryKey: ["notifications"],
    queryFn: () =>
      apiRequest<Notification[]>(
        "/notifications?limit=20",
      ),
    enabled: isOpen,
  });

  const readMutation = useMutation({
    mutationFn: (notificationId: number) =>
      apiRequest<Notification>(
        `/notifications/${notificationId}/read`,
        {
          method: "PATCH",
        },
      ),

    onSuccess: async () => {
      await refreshNotifications(
        queryClient,
      );
    },
  });

  const readAllMutation = useMutation({
    mutationFn: () =>
      apiRequest<NotificationUnreadCount>(
        "/notifications/read-all",
        {
          method: "PATCH",
        },
      ),

    onSuccess: async () => {
      await refreshNotifications(
        queryClient,
      );
    },
  });

  const unreadCount =
    countQuery.data?.unread_count ?? 0;

  return (
    <div className="fixed right-5 top-5 z-50">
      <button
        type="button"
        aria-label="Afficher les notifications"
        aria-expanded={isOpen}
        onClick={() =>
          setIsOpen((current) => !current)
        }
        className="relative flex h-12 w-12 items-center justify-center rounded-full border border-slate-700 bg-slate-900 text-xl shadow-lg transition hover:border-cyan-500"
      >
        <span aria-hidden="true">🔔</span>

        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-1 flex min-h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-xs font-bold text-white">
            {unreadCount > 99
              ? "99+"
              : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <section className="mt-3 w-[calc(100vw-2.5rem)] max-w-md overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
          <header className="flex items-center justify-between border-b border-slate-800 p-4">
            <div>
              <h2 className="font-semibold">
                Notifications
              </h2>

              <p className="mt-1 text-xs text-slate-400">
                {unreadCount} non lue
                {unreadCount > 1 ? "s" : ""}
              </p>
            </div>

            <button
              type="button"
              disabled={
                unreadCount === 0 ||
                readAllMutation.isPending
              }
              onClick={() =>
                readAllMutation.mutate()
              }
              className="text-xs font-semibold text-cyan-400 transition hover:text-cyan-300 disabled:cursor-not-allowed disabled:text-slate-600"
            >
              Tout marquer comme lu
            </button>
          </header>

          <div className="max-h-[70vh] overflow-y-auto">
            {notificationsQuery.isLoading && (
              <p className="p-6 text-center text-sm text-slate-400">
                Chargement...
              </p>
            )}

            {notificationsQuery.error && (
              <p className="p-6 text-sm text-red-300">
                Impossible de charger les
                notifications.
              </p>
            )}

            {!notificationsQuery.isLoading &&
              notificationsQuery.data?.length ===
                0 && (
                <p className="p-6 text-center text-sm text-slate-400">
                  Aucune notification.
                </p>
              )}

            {notificationsQuery.data?.map(
              (notification) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                  isPending={
                    readMutation.isPending &&
                    readMutation.variables ===
                      notification.id
                  }
                  onRead={() =>
                    readMutation.mutate(
                      notification.id,
                    )
                  }
                />
              ),
            )}
          </div>
        </section>
      )}
    </div>
  );
}

interface NotificationItemProps {
  notification: Notification;
  isPending: boolean;
  onRead: () => void;
}

function NotificationItem({
  notification,
  isPending,
  onRead,
}: NotificationItemProps) {
  const content = (
    <>
      <div className="flex items-start gap-3">
        <span
          className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${levelColor(
            notification.level,
          )}`}
        />

        <div className="min-w-0 flex-1">
          <div className="flex gap-2">
            <h3 className="flex-1 text-sm font-semibold">
              {notification.title}
            </h3>

            {!notification.is_read && (
              <span className="mt-1 h-2 w-2 rounded-full bg-cyan-400" />
            )}
          </div>

          <p className="mt-1 text-sm text-slate-400">
            {notification.message}
          </p>

          <p className="mt-2 text-xs text-slate-600">
            {formatDate(
              notification.created_at,
            )}
          </p>
        </div>
      </div>
    </>
  );

  return (
    <article
      className={
        notification.is_read
          ? "border-b border-slate-800 p-4"
          : "border-b border-slate-800 bg-cyan-950/20 p-4"
      }
    >
      {notification.target_url ? (
        <a
          href={notification.target_url}
          onClick={() => {
            if (!notification.is_read) {
              onRead();
            }
          }}
          className="block"
        >
          {content}
        </a>
      ) : (
        content
      )}

      {!notification.is_read && (
        <button
          type="button"
          disabled={isPending}
          onClick={onRead}
          className="mt-3 text-xs font-semibold text-cyan-400 hover:text-cyan-300 disabled:opacity-50"
        >
          Marquer comme lue
        </button>
      )}
    </article>
  );
}

function levelColor(
  level: NotificationLevel,
): string {
  const colors: Record<
    NotificationLevel,
    string
  > = {
    info: "bg-cyan-400",
    success: "bg-emerald-400",
    warning: "bg-amber-400",
    error: "bg-red-400",
  };

  return colors[level];
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(
    "fr-FR",
    {
      dateStyle: "short",
      timeStyle: "short",
    },
  ).format(new Date(value));
}

async function refreshNotifications(
  queryClient: ReturnType<
    typeof useQueryClient
  >,
): Promise<void> {
  await Promise.all([
    queryClient.invalidateQueries({
      queryKey: ["notifications"],
    }),
    queryClient.invalidateQueries({
      queryKey: [
        "notifications",
        "unread-count",
      ],
    }),
  ]);
}