// Placeholder used by pages that aren't built yet. Delete once a page is real.
export default function Stub({ title, owner, todo }: { title: string; owner: string; todo: string[] }) {
  return (
    <section className="rounded-lg border border-dashed border-black/20 bg-white p-6">
      <h1 className="text-xl font-semibold">{title}</h1>
      <p className="mt-1 text-sm text-black/60">Owner: {owner}</p>
      <ul className="mt-4 list-disc space-y-1 pl-5 text-sm">
        {todo.map((t) => <li key={t}>{t}</li>)}
      </ul>
    </section>
  )
}
