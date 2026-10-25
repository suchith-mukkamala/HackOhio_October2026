import Feed from './Feed'
import ProjectFocus from '../components/ProjectFocus'
import { useMe } from '../lib/auth'

export default function Home() {
  const { data: me } = useMe()
  if (!me) return null
  return <div className="flex min-w-0 flex-col gap-4">
    <ProjectFocus me={me} />
    <section aria-labelledby="community-progress-heading" className="min-w-0">
      <div className="mb-3"><h2 id="community-progress-heading" className="text-lg font-semibold">Community progress</h2></div>
      <Feed />
    </section>
  </div>
}
