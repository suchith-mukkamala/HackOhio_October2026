// Placeholder used by pages that aren't built yet. Delete once a page is real.
export default function Stub({ title, owner, todo }: { title: string; owner: string; todo: string[] }) {
  return (
    <section className="max-w-2xl rounded-2xl border border-dashed border-edge bg-card p-6">
      <h1 className="text-xl font-semibold">{title}</h1>
      <p className="mt-1 text-sm text-muted">Owner: {owner}</p>
      <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-ink/80">
        {todo.map((t) => <li key={t}>{t}</li>)}
      </ul>
    </section>
  )
}
