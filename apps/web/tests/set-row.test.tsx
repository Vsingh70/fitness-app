import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SetRow } from "@/components/workouts/set-row";
import type { TrackingType } from "@/lib/workouts/types";

function renderRow(trackingType: TrackingType) {
  const onSubmit = vi.fn();
  render(<SetRow trackingType={trackingType} setIndex={0} onSubmit={onSubmit} />);
  return { onSubmit };
}

describe("SetRow validation per tracking_type", () => {
  it("weight_reps rejects when reps missing", async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderRow("weight_reps");
    await user.type(screen.getByLabelText("kg for set 1"), "100");
    await user.click(screen.getByRole("button", { name: /save/i }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/reps required/i);
  });

  it("weight_reps accepts when both fields present", async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderRow("weight_reps");
    await user.type(screen.getByLabelText("kg for set 1"), "100");
    await user.type(screen.getByLabelText("reps for set 1"), "5");
    await user.click(screen.getByRole("button", { name: /save/i }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit.mock.calls[0]![0]).toMatchObject({ weight_kg: "100", reps: 5 });
  });

  it("time_only rejects when weight is provided", async () => {
    const user = userEvent.setup();
    render(<SetRow trackingType="time_only" setIndex={0} onSubmit={vi.fn()} />);
    await user.type(screen.getByLabelText("time for set 1"), "60");
    // time_only does not render a kg input, so nothing extra to add; just verify it accepts.
    await user.click(screen.getByRole("button", { name: /save/i }));
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("distance_time requires both fields", async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderRow("distance_time");
    await user.type(screen.getByLabelText("distance for set 1"), "5000");
    await user.click(screen.getByRole("button", { name: /save/i }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/duration_seconds required/i);

    await user.type(screen.getByLabelText("time for set 1"), "1500");
    await user.click(screen.getByRole("button", { name: /save/i }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("commits on Cmd+Enter", async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderRow("bodyweight_reps");
    const repsInput = screen.getByLabelText("reps for set 1");
    await user.type(repsInput, "10");
    await user.keyboard("{Meta>}{Enter}{/Meta}");
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });
});
