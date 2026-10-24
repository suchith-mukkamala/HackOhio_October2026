import assert from 'node:assert/strict'
import { createSearchIndex } from '../src/lib/exploreSearch.ts'

const index = createSearchIndex([
  { id: 'maya', fields: [{ text: 'Maya Chen', weight: 5 }, { text: 'Python SQL café C++', weight: 4 }] },
  { id: 'sam', fields: [{ text: 'Sam Okafor', weight: 5 }, { text: 'Python FastAPI', weight: 4 }] },
  { id: 'priya', fields: [{ text: 'Priya Natarajan', weight: 5 }, { text: 'Design Figma', weight: 4 }] },
  { id: 'mayank', fields: [{ text: 'Mayank', weight: 5 }] },
])
const ids = query => index.search(query).map(hit => hit.id)
assert.equal(ids('')[0], 'maya')
assert.equal(ids('   ').length, 4)
assert.deepEqual(ids('CHEN'), ['maya'])
assert.ok(ids('nat').includes('priya'))
assert.ok(ids('taraj').includes('priya')) // Interior substring, not just prefix.
for (const typo of ['pyhton', 'pyton', 'pythonn', 'pythom']) {
  assert.deepEqual(new Set(ids(typo)), new Set(['maya', 'sam']), typo)
  assert.ok(index.search(typo).every(hit => hit.fuzzy))
}
assert.equal(ids('maya')[0], 'maya') // Exact before prefix and fuzzy.
assert.deepEqual(ids('Sam pyhton'), ['sam']) // All terms must match the same record.
assert.deepEqual(ids('Maya Design'), [])
assert.deepEqual(ids('zzzzzzzz'), [])
assert.deepEqual(ids('cafe'), ['maya'])
assert.deepEqual(ids('C++'), ['maya'])
assert.deepEqual(ids('py'), ['maya', 'sam'])
assert.deepEqual(ids('pytxon sql'), ['maya'])
assert.deepEqual(ids('x'.repeat(160)), [])
console.log('Explore search checks passed: exact, partial, typo, ranking, multiple terms, normalization, and empty results.')
