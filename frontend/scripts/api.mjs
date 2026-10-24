// Starts the FastAPI backend from backend/.venv so `npm run dev` runs the whole app.
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const backend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../backend')
const python = path.join(backend, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')

if (!existsSync(python)) {
  console.error('backend/.venv not found. Set up the backend first (see README).')
  process.exit(1)
}

// On Windows, uvicorn's reload sends a Ctrl+C to its whole console, which also killed Vite.
// A separate (hidden) console keeps that Ctrl+C inside the backend.
const isWindows = process.platform === 'win32'
spawn(python, ['-m', 'uvicorn', 'app.main:app', '--reload', '--reload-dir', 'app', '--port', '8000'], { cwd: backend, stdio: 'inherit', detached: isWindows, windowsHide: true })
  .on('exit', (code) => process.exit(code ?? 0))
