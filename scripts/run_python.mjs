import { spawnSync } from 'node:child_process'
import process from 'node:process'

const args = process.argv.slice(2)
if (!args.length) {
  console.error('Usage: node scripts/run_python.mjs <script> [...args]')
  process.exit(2)
}

const candidates = process.env.PYTHON
  ? [process.env.PYTHON]
  : process.platform === 'win32'
    ? ['python', 'py']
    : ['python3', 'python']

for (const command of candidates) {
  const probeArgs = command === 'py' ? ['-3', '--version'] : ['--version']
  const probe = spawnSync(command, probeArgs, { stdio: 'ignore' })
  if (probe.status !== 0) continue

  const commandArgs = command === 'py' ? ['-3', ...args] : args
  const result = spawnSync(command, commandArgs, { stdio: 'inherit' })
  process.exit(result.status ?? 1)
}

console.error('Python 3 was not found. Install Python 3.12+ or set the PYTHON environment variable.')
process.exit(2)
