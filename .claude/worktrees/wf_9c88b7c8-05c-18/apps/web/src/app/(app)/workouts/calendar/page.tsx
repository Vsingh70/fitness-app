import { redirect } from "next/navigation";

export default function WorkoutsCalendarRedirect(): never {
  redirect("/calendar");
}
