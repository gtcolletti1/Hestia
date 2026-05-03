/**
 * Tests for AgendaBlock viewport-aware spill (PRD §2.12.1).
 *
 * The block must:
 * 1. Render every day when the parent has room.
 * 2. Trim trailing days one-at-a-time when the rendered list is taller
 *    than the parent.
 * 3. Surface a "+N more days" footer when at least one day was hidden.
 * 4. Always show at least one day (never collapse to empty).
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, act } from "@testing-library/react";
import { AgendaBlock } from "@/components/splash/SplashContent";
import type { SplashDay } from "@/types/splash";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function makeDays(n: number): SplashDay[] {
  return Array.from({ length: n }, (_, i) => ({
    date: `2026-05-${String(i + 1).padStart(2, "0")}`,
    label: `Day ${i + 1}`,
    events: [
      {
        id: `ev-${i}`,
        title: `Event on day ${i + 1}`,
        location: null,
        start_time: `2026-05-${String(i + 1).padStart(2, "0")}T09:00:00Z`,
        end_time: `2026-05-${String(i + 1).padStart(2, "0")}T10:00:00Z`,
        all_day: false,
        color: null,
        profile_name: "Sam",
        profile_color: "#3B82F6",
      },
    ],
  }));
}

/**
 * Force jsdom to report fake layout dimensions on the wrapper +
 * its first child so the spill measurement actually does something.
 *
 * The spill logic shrinks visibleCount whenever
 *   firstElementChild.scrollHeight > container.clientHeight + 1.
 *
 * We make:
 *   - container.clientHeight = 200 (constant)
 *   - child.scrollHeight    = 50 * (rendered day count)
 * which means the block fits exactly 4 days.
 */
function installLayoutMocks(parentHeight: number, perDayHeight: number) {
  Object.defineProperty(HTMLElement.prototype, "clientHeight", {
    configurable: true,
    get(this: HTMLElement) {
      // The AgendaBlock wrapper has `overflow-hidden` and contains exactly
      // one child <div class="space-y-4">. We treat any element whose
      // first child is the day list as the "container".
      if (this.firstElementChild?.classList.contains("space-y-4")) {
        return parentHeight;
      }
      return 0;
    },
  });
  Object.defineProperty(HTMLElement.prototype, "scrollHeight", {
    configurable: true,
    get(this: HTMLElement) {
      if (this.classList.contains("space-y-4")) {
        // Each rendered DayRow plus the optional "+N more" footer.
        return this.children.length * perDayHeight;
      }
      return 0;
    },
  });
}

describe("AgendaBlock viewport-aware spill", () => {
  it("renders all days when they fit", async () => {
    installLayoutMocks(/* parent */ 1000, /* perDay */ 50);
    render(<AgendaBlock days={makeDays(3)} timeFormat="12h" />);
    // Run the rAF the layout effect schedules.
    await act(async () => {
      await new Promise((r) => requestAnimationFrame(() => r(null)));
    });
    expect(screen.getByText("Day 1")).toBeInTheDocument();
    expect(screen.getByText("Day 2")).toBeInTheDocument();
    expect(screen.getByText("Day 3")).toBeInTheDocument();
    expect(screen.queryByText(/more day/)).not.toBeInTheDocument();
  });

  it("trims trailing days and surfaces a +N more footer when overflowing", async () => {
    // Parent fits 4 children at 50px each; we ask for 7 days. The
    // recursive shrink should land somewhere between 1 and 4 days
    // visible (the +N footer also counts as a child, so the stable
    // visible count is 3 days + footer = 4 children).
    installLayoutMocks(200, 50);
    render(<AgendaBlock days={makeDays(7)} timeFormat="12h" />);

    // The spill loop runs across multiple rAF/effect passes.
    for (let i = 0; i < 10; i++) {
      // eslint-disable-next-line no-await-in-loop
      await act(async () => {
        await new Promise((r) => requestAnimationFrame(() => r(null)));
      });
    }

    expect(screen.getByText("Day 1")).toBeInTheDocument();
    // The last day must have been trimmed.
    expect(screen.queryByText("Day 7")).not.toBeInTheDocument();
    // Footer must surface the spill count.
    expect(screen.getByText(/more days?/)).toBeInTheDocument();
  });

  it("never collapses below one visible day even when nothing fits", async () => {
    // Parent is tiny; per-day cost is huge — every measurement overflows.
    installLayoutMocks(10, 500);
    render(<AgendaBlock days={makeDays(5)} timeFormat="12h" />);

    for (let i = 0; i < 10; i++) {
      // eslint-disable-next-line no-await-in-loop
      await act(async () => {
        await new Promise((r) => requestAnimationFrame(() => r(null)));
      });
    }

    expect(screen.getByText("Day 1")).toBeInTheDocument();
    expect(screen.getByText(/^\+4 more days$/)).toBeInTheDocument();
  });

  it("uses singular 'day' in the footer when exactly one is hidden", async () => {
    // 3 days × 50px = 150px. Parent fits 100px, so the loop trims one
    // day (2 days + footer = 3 children = 150px = still > 101). Then
    // it trims again to (1 day + footer = 2 children = 100px ≤ 101)
    // and stabilises with 2 hidden... so use a parent that lands at
    // exactly 1 hidden:
    //   parent = 140px → 3 days (150) overflows → shrink to 2 days
    //   2 days + footer = 3 children = 150px → still > 141, shrink again
    // The simplest path to "+1 more day" is 2 source days, parent = 49.
    installLayoutMocks(49, 50);
    render(<AgendaBlock days={makeDays(2)} timeFormat="12h" />);

    for (let i = 0; i < 10; i++) {
      // eslint-disable-next-line no-await-in-loop
      await act(async () => {
        await new Promise((r) => requestAnimationFrame(() => r(null)));
      });
    }

    expect(screen.getByText(/^\+1 more day$/)).toBeInTheDocument();
  });
});
