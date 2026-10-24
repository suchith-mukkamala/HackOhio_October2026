import type { User } from '../lib/types'

const initials = (name: string) =>
  name.split(' ').filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase()

export default function Avatar({ user, size = 40 }: { user: Pick<User, 'name' | 'avatar_url'>; size?: number }) {
  const style = { width: size, height: size, fontSize: size * 0.38 }
  return user.avatar_url ? (
    <img src={user.avatar_url} alt="" style={style} className="shrink-0 rounded-full object-cover" />
  ) : (
    <span style={style} className="grid shrink-0 place-items-center rounded-full bg-avatar font-semibold text-white">
      {initials(user.name)}
    </span>
  )
}
