import { useState } from "react";
import SplashView from "@/components/splash/SplashView";
import type { SplashCalendarMode, SplashMode } from "@/types/splash";

export interface SplashSettingsValues {
  splash_mode: SplashMode;
  splash_alternating_ambient_seconds: number;
  splash_alternating_photo_seconds: number;
  splash_calendar_mode: SplashCalendarMode;
  splash_agenda_max_days: number;
  splash_show_routines: boolean;
  splash_show_meals: boolean;
  splash_show_weather: boolean;
  splash_show_messages: boolean;
}

interface Props {
  values: SplashSettingsValues;
  onChange: (patch: Partial<SplashSettingsValues>) => void;
  disabled?: boolean;
}

const MODE_OPTIONS: { value: SplashMode; label: string; help: string }[] = [
  {
    value: "ambient",
    label: "Ambient agenda",
    help: "Shows today's agenda, routines, and household info.",
  },
  {
    value: "photo",
    label: "Photo frame",
    help: "Cycles through your uploaded family photos.",
  },
  {
    value: "alternating",
    label: "Alternating",
    help: "Flips between the ambient view and photos.",
  },
];

const CAL_OPTIONS: { value: SplashCalendarMode; label: string; help: string }[] = [
  {
    value: "off",
    label: "Off — show full details",
    help: "Anyone in the room can see event titles, times, and locations.",
  },
  {
    value: "busy_only",
    label: "Busy only",
    help: "Times and person colors show, but titles say \"Busy\" and locations are hidden.",
  },
  {
    value: "hidden",
    label: "Hidden",
    help: "The agenda block is removed from the splash entirely.",
  },
];

/**
 * Admin UI for the pre-login splash + privacy policy (PRD §2.12).
 *
 * Each control auto-saves through the parent's ``onChange`` (the parent
 * is responsible for persisting via the settings mutation). Below the
 * controls, a "Preview splash" panel renders the SplashView in a
 * sandboxed frame so admins can see the effect of each setting on a
 * passerby's view immediately, without waiting for the screensaver
 * timeout.
 */
export default function SplashSettingsSection({ values, onChange, disabled }: Props) {
  const [previewMode, setPreviewMode] = useState<SplashMode | null>(null);

  return (
    <section className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
        🖼️ Splash &amp; Pre-login Privacy
      </h3>
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
        Controls what an unauthenticated person standing in front of the display
        can see. Logged-in family members always see full details.
      </p>

      {/* Mode */}
      <fieldset className="mb-6" disabled={disabled}>
        <legend className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2">
          Splash mode
        </legend>
        <div className="space-y-2">
          {MODE_OPTIONS.map((opt) => (
            <label
              key={opt.value}
              className="flex items-start gap-3 cursor-pointer rounded-lg p-2 hover:bg-gray-50 dark:hover:bg-gray-700/40"
            >
              <input
                type="radio"
                name="splash_mode"
                className="mt-1"
                checked={values.splash_mode === opt.value}
                onChange={() => onChange({ splash_mode: opt.value })}
              />
              <div>
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {opt.label}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {opt.help}
                </div>
              </div>
            </label>
          ))}
        </div>
      </fieldset>

      {values.splash_mode === "alternating" && (
        <fieldset className="mb-6 grid grid-cols-1 sm:grid-cols-2 gap-4" disabled={disabled}>
          <NumberField
            label="Ambient dwell (seconds)"
            value={values.splash_alternating_ambient_seconds}
            min={10}
            max={600}
            onChange={(n) => onChange({ splash_alternating_ambient_seconds: n })}
          />
          <NumberField
            label="Photo dwell (seconds)"
            value={values.splash_alternating_photo_seconds}
            min={10}
            max={600}
            onChange={(n) => onChange({ splash_alternating_photo_seconds: n })}
          />
        </fieldset>
      )}

      {/* Calendar disclosure */}
      <fieldset className="mb-6" disabled={disabled}>
        <legend className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2">
          Calendar disclosure
        </legend>
        <div className="space-y-2">
          {CAL_OPTIONS.map((opt) => (
            <label
              key={opt.value}
              className="flex items-start gap-3 cursor-pointer rounded-lg p-2 hover:bg-gray-50 dark:hover:bg-gray-700/40"
            >
              <input
                type="radio"
                name="splash_calendar_mode"
                className="mt-1"
                checked={values.splash_calendar_mode === opt.value}
                onChange={() => onChange({ splash_calendar_mode: opt.value })}
              />
              <div>
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {opt.label}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {opt.help}
                </div>
              </div>
            </label>
          ))}
        </div>
      </fieldset>

      {/* Agenda days */}
      <fieldset className="mb-6" disabled={disabled || values.splash_calendar_mode === "hidden"}>
        <NumberField
          label="Days of agenda to show (max)"
          value={values.splash_agenda_max_days}
          min={1}
          max={7}
          onChange={(n) => onChange({ splash_agenda_max_days: n })}
          help="The splash will stop early if the next day wouldn't fit on screen."
        />
      </fieldset>

      {/* Per-section toggles */}
      <fieldset className="mb-6" disabled={disabled}>
        <legend className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2">
          Show on splash
        </legend>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <Toggle
            label="Routines"
            value={values.splash_show_routines}
            onChange={(v) => onChange({ splash_show_routines: v })}
          />
          <Toggle
            label="Today's meals"
            value={values.splash_show_meals}
            onChange={(v) => onChange({ splash_show_meals: v })}
            help="Off by default — meal names can be revealing."
          />
          <Toggle
            label="Weather"
            value={values.splash_show_weather}
            onChange={(v) => onChange({ splash_show_weather: v })}
          />
          <Toggle
            label="Pinned messages"
            value={values.splash_show_messages}
            onChange={(v) => onChange({ splash_show_messages: v })}
            help="Off by default — pinned notes can be sensitive."
          />
        </div>
      </fieldset>

      {/* Preview */}
      <div className="mt-6 border-t border-gray-200 dark:border-gray-700 pt-4">
        <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
          <div>
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-200">
              Preview splash
            </h4>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              See what a passerby would see right now. Alternating runs in
              fast-forward (~10 s per side).
            </p>
          </div>
          <div className="flex gap-2">
            <PreviewButton
              label="Ambient"
              active={previewMode === "ambient"}
              onClick={() => setPreviewMode("ambient")}
            />
            <PreviewButton
              label="Photo"
              active={previewMode === "photo"}
              onClick={() => setPreviewMode("photo")}
            />
            <PreviewButton
              label="Alternating"
              active={previewMode === "alternating"}
              onClick={() => setPreviewMode("alternating")}
            />
            {previewMode && (
              <button
                type="button"
                onClick={() => setPreviewMode(null)}
                className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Close
              </button>
            )}
          </div>
        </div>

        {previewMode && (
          <div className="relative w-full overflow-hidden rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-900" style={{ aspectRatio: "16 / 10" }}>
            <SplashView
              previewMode={previewMode}
              disableUnlock
              onUnlock={() => {
                /* no-op: preview swallows the tap */
              }}
            />
          </div>
        )}
      </div>
    </section>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  onChange,
  help,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (n: number) => void;
  help?: string;
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-gray-700 dark:text-gray-200">{label}</span>
      <input
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={(e) => {
          const n = Number(e.target.value);
          if (Number.isFinite(n)) {
            onChange(Math.min(max, Math.max(min, Math.round(n))));
          }
        }}
        className="mt-1 block w-32 rounded-md border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-2 py-1 text-sm"
      />
      {help && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{help}</p>}
    </label>
  );
}

function Toggle({
  label,
  value,
  onChange,
  help,
}: {
  label: string;
  value: boolean;
  onChange: (v: boolean) => void;
  help?: string;
}) {
  return (
    <div className="flex items-start gap-3 p-2">
      <button
        type="button"
        onClick={() => onChange(!value)}
        className={`mt-0.5 relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors ${
          value ? "bg-amber-500" : "bg-gray-300 dark:bg-gray-600"
        }`}
        aria-pressed={value}
        aria-label={label}
      >
        <span
          className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
            value ? "translate-x-5" : "translate-x-0.5"
          }`}
        />
      </button>
      <div>
        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{label}</div>
        {help && <div className="text-xs text-gray-500 dark:text-gray-400">{help}</div>}
      </div>
    </div>
  );
}

function PreviewButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
        active
          ? "border-amber-500 bg-amber-500 text-white"
          : "border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700"
      }`}
    >
      {label}
    </button>
  );
}
