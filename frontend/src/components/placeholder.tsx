export default function PlaceholderPage({
  title,
  body,
}: {
  title: string;
  body: string;
}) {
  return (
    <div className="glass shadow-soft fade-up rounded-[2rem] p-8">
      <p className="text-xs uppercase tracking-[0.24em] text-forest">Coming next</p>
      <h2 className="display mt-2 text-4xl text-ink">{title}</h2>
      <p className="mt-3 max-w-2xl text-sm text-ink/65 md:text-base">{body}</p>
    </div>
  );
}
