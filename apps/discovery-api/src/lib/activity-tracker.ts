"use client";

interface ActivityEvent {
  event: string;
  paintingId?: string;
  position?: number;
  source?: string;
  metadata?: Record<string, unknown>;
  timestamp?: number;
}

class ActivityTracker {
  private queue: ActivityEvent[] = [];
  private flushInterval = 2000; // 2 seconds
  private visitorId: string = "";
  private sessionId: string = "";
  private intervalId: ReturnType<typeof setInterval> | null = null;

  constructor() {
    if (typeof window === "undefined") return;

    this.visitorId = this.getOrCreateVisitorId();
    this.sessionId = this.createSessionId();

    // Periodic flush
    this.intervalId = setInterval(() => this.flush(), this.flushInterval);

    // Flush on page hide
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") {
        this.flush();
      }
    });

    // Flush before unload
    window.addEventListener("beforeunload", () => {
      this.flush();
    });

    // Track session start
    this.track({ event: "session_start" });
  }

  track(event: ActivityEvent) {
    this.queue.push({
      ...event,
      timestamp: Date.now(),
    });
  }

  getVisitorId(): string {
    return this.visitorId;
  }

  getSessionId(): string {
    return this.sessionId;
  }

  private async flush() {
    if (this.queue.length === 0) return;

    const events = this.queue.map((e) => ({
      ...e,
      visitorId: this.visitorId,
      sessionId: this.sessionId,
    }));

    this.queue = [];

    try {
      await fetch("/api/activity", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ events }),
        keepalive: true,
      });
    } catch (e) {
      // Re-queue on failure
      console.error("Failed to flush activities:", e);
      this.queue.unshift(...events);
    }
  }

  private getOrCreateVisitorId(): string {
    const key = "artwall_visitor_id";
    let id = localStorage.getItem(key);
    if (!id) {
      id = "v_" + crypto.randomUUID();
      localStorage.setItem(key, id);
    }
    return id;
  }

  private createSessionId(): string {
    return "s_" + crypto.randomUUID();
  }

  destroy() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
    this.flush();
  }
}

// Singleton instance
let tracker: ActivityTracker | null = null;

export function getTracker(): ActivityTracker {
  if (typeof window === "undefined") {
    // Return a no-op tracker for SSR
    return {
      track: () => {},
      getVisitorId: () => "",
      getSessionId: () => "",
      destroy: () => {},
    } as unknown as ActivityTracker;
  }

  if (!tracker) {
    tracker = new ActivityTracker();
  }
  return tracker;
}

export { ActivityTracker };
