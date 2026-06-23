import { redirect } from "next/navigation";

export default function BodyRedirect(): never {
  redirect("/health");
}
