import { redirect } from "next/navigation";

export default function ProjectPage({
  params,
}: {
  params: { id: string };
}) {
  redirect(`/project/${params.id}/configure`);
}
