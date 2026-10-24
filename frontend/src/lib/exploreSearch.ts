/** Local inverted index. Rebuild when the source data changes, not on each keystroke. */
export type SearchDocument = { id: string; fields: { text: string; weight: number }[] }

const normalize = (text: string) => text.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
const tokenize = (text: string) => normalize(text).match(/[a-z0-9+#]+/g) ?? []

function signatures(word: string) {
  return new Set([word, ...Array.from(word, (_, i) => word.slice(0, i) + word.slice(i + 1))])
}

// One insertion, deletion, substitution, or adjacent transposition. Linear verification.
function oneTypo(a: string, b: string): boolean {
  if (Math.abs(a.length - b.length) > 1) return false
  let i = 0
  while (i < Math.min(a.length, b.length) && a[i] === b[i]) i++
  if (i === Math.min(a.length, b.length)) return true
  if (a.length === b.length) {
    return a.slice(i + 1) === b.slice(i + 1) ||
      (a[i] === b[i + 1] && a[i + 1] === b[i] && a.slice(i + 2) === b.slice(i + 2))
  }
  return a.length > b.length ? a.slice(i + 1) === b.slice(i) : a.slice(i) === b.slice(i + 1)
}

function add<K, V>(map: Map<K, Set<V>>, key: K, value: V) {
  if (!map.has(key)) map.set(key, new Set())
  map.get(key)!.add(value)
}

export function createSearchIndex(documents: SearchDocument[]) {
  const postings = new Map<string, Map<string, number>>()
  const grams = new Map<string, Set<string>>()
  const deletions = new Map<string, Set<string>>()

  for (const document of documents) {
    for (const field of document.fields) {
      for (const word of tokenize(field.text)) {
        if (!postings.has(word)) postings.set(word, new Map())
        const hits = postings.get(word)!
        hits.set(document.id, Math.max(hits.get(document.id) ?? 0, field.weight))
      }
    }
  }
  for (const word of postings.keys()) {
    // 1–3 character grams support prefixes AND matches inside a word.
    for (let size = 1; size <= Math.min(3, word.length); size++) {
      for (let i = 0; i <= word.length - size; i++) add(grams, word.slice(i, i + size), word)
    }
    for (const signature of signatures(word)) add(deletions, signature, word)
  }

  return {
    search(query: string): { id: string; score: number; fuzzy: boolean }[] {
      const tokens = [...new Set(tokenize(query))]
      if (!tokens.length) return documents.map(({ id }) => ({ id, score: 0, fuzzy: false }))
      let matches: Map<string, { score: number; fuzzy: boolean }> | undefined
      for (const token of tokens) {
        const size = Math.min(3, token.length)
        const buckets = Array.from({ length: token.length - size + 1 }, (_, i) => grams.get(token.slice(i, i + size)) ?? new Set<string>())
        buckets.sort((a, b) => a.size - b.size)
        const candidates = new Set([...buckets[0]].filter(word => buckets.every(bucket => bucket.has(word)) && word.includes(token)))
        // Skip fuzzy expansion for tiny queries, where unrelated matches would overwhelm results.
        if (token.length >= 3 && token.length <= 64) {
          for (const signature of signatures(token)) {
            for (const word of deletions.get(signature) ?? []) {
              if (oneTypo(token, word)) candidates.add(word)
            }
          }
        }
        const hits = new Map<string, { score: number; fuzzy: boolean }>()
        for (const word of candidates) {
          const quality = word === token ? 4 : word.startsWith(token) ? 3 : word.includes(token) ? 2 : 1
          for (const [id, weight] of postings.get(word)!) {
            const score = quality * weight
            if (score > (hits.get(id)?.score ?? 0)) hits.set(id, { score, fuzzy: quality === 1 })
          }
        }
        const previous = matches
        matches = new Map([...hits].flatMap(([id, hit]) => {
          if (!previous) return [[id, hit]]
          const prior = previous.get(id)
          return prior ? [[id, { score: hit.score + prior.score, fuzzy: hit.fuzzy || prior.fuzzy }]] : []
        }))
        if (!matches.size) return []
      }
      return [...matches!].map(([id, hit]) => ({ id, ...hit })).sort((a, b) => Number(a.fuzzy) - Number(b.fuzzy) || b.score - a.score || a.id.localeCompare(b.id))
    },
  }
}
