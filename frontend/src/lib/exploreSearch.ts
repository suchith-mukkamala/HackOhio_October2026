export type SearchDocument = {
  id: string
  fields: { text: string; weight: number }[]
}

type SearchHit = {
  id: string
  score: number
  fuzzy: boolean
}

type TokenMatch = {
  score: number
  fuzzy: boolean
}

const normalize = (text: string) =>
  text
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()

const tokenize = (text: string) => normalize(text).match(/[a-z0-9]+/g) ?? []

function oneTypoAway(a: string, b: string): boolean {
  if (Math.abs(a.length - b.length) > 1) return false

  let left = 0
  while (left < Math.min(a.length, b.length) && a[left] === b[left]) left += 1
  if (left === Math.min(a.length, b.length)) return true

  if (a.length === b.length) {
    return (
      a.slice(left + 1) === b.slice(left + 1) ||
      (a[left] === b[left + 1] && a[left + 1] === b[left] && a.slice(left + 2) === b.slice(left + 2))
    )
  }

  const [longer, shorter] = a.length > b.length ? [a, b] : [b, a]
  return longer.slice(left + 1) === shorter.slice(left)
}

function scoreToken(token: string, word: string): TokenMatch | null {
  if (word === token) return { score: 12, fuzzy: false }
  if (word.startsWith(token)) return { score: 8, fuzzy: false }
  if (token.length >= 4 && word.includes(token)) return { score: 4, fuzzy: false }
  if (token.length >= 4 && oneTypoAway(token, word)) return { score: 2, fuzzy: true }
  return null
}

export function createSearchIndex(documents: SearchDocument[]) {
  const indexed = documents.map((document) => ({
    id: document.id,
    fields: document.fields.map((field) => ({
      text: normalize(field.text),
      weight: field.weight,
      words: tokenize(field.text),
    })),
  }))

  return {
    search(query: string): SearchHit[] {
      const tokens = tokenize(query)
      if (!tokens.length) return documents.map(({ id }) => ({ id, score: 0, fuzzy: false }))

      const normalizedQuery = tokens.join(' ')
      const hits: SearchHit[] = []

      for (const document of indexed) {
        let score = 0
        let fuzzy = false
        let matchedEveryToken = true

        for (const token of tokens) {
          let best: TokenMatch | null = null
          let bestWeight = 0

          for (const field of document.fields) {
            for (const word of field.words) {
              const match = scoreToken(token, word)
              if (!match) continue

              const weightedScore = match.score * field.weight
              if (!best || weightedScore > best.score * bestWeight) {
                best = match
                bestWeight = field.weight
              }
            }
          }

          if (!best) {
            matchedEveryToken = false
            break
          }

          score += best.score * bestWeight
          fuzzy ||= best.fuzzy
        }

        if (!matchedEveryToken) continue

        for (const field of document.fields) {
          if (field.text.includes(normalizedQuery)) score += 6 * field.weight
        }

        hits.push({ id: document.id, score, fuzzy })
      }

      return hits.sort((a, b) =>
        b.score - a.score || Number(a.fuzzy) - Number(b.fuzzy) || a.id.localeCompare(b.id),
      )
    },
  }
}
