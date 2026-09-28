// npm 配布用パッケージを dist/npm/main に生成し、必要なら公開する。
//
//   node npm/build.mjs <version>             ビルドのみ（例: 1.0.0。__init__.py の __version__ と一致させる）
//   node npm/build.mjs <version> --publish   ビルドして npm に公開（公開済みの版は飛ばす）
//   node npm/build.mjs <version> --pack      ビルドして .tgz を作る（ローカル確認用）
//
// 標準ライブラリだけで動く Python 製 CLI なので、ソースを lib/ に同梱し、
// bin/ の JS シムがシステムの Python で起動する（OS/CPU 別パッケージは不要）。
import { execFileSync } from 'node:child_process';
import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const MOD = 'clilap_codepush'; // 同梱する Python パッケージ（src/ の下）

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const out = join(root, 'dist', 'npm');

const [version, ...flags] = process.argv.slice(2);
if (!/^\d+\.\d+\.\d+(-[\w.]+)?$/.test(version ?? '')) {
  console.error('使い方: node npm/build.mjs <version> [--publish|--pack]');
  process.exit(2);
}
const pyVersion = readFileSync(join(root, 'src', MOD, '__init__.py'), 'utf8').match(/__version__ = "([^"]+)"/)?.[1];
if (pyVersion !== version && !version.includes('-')) {
  console.error(`src/${MOD}/__init__.py の __version__ (${pyVersion}) と ${version} が一致しません`);
  process.exit(1);
}

const main = JSON.parse(readFileSync(join(root, 'npm', 'package', 'package.json'), 'utf8'));
const run = (cmd, args, opts = {}) => execFileSync(cmd, args, { stdio: 'inherit', ...opts });

rmSync(out, { recursive: true, force: true });
const dir = join(out, 'main');
cpSync(join(root, 'npm', 'package'), dir, { recursive: true });
mkdirSync(join(dir, 'lib'));
cpSync(join(root, 'src', MOD), join(dir, 'lib', MOD), {
  recursive: true,
  filter: (src) => !/__pycache__|\.pyc$/.test(src),
});
cpSync(join(root, 'README.md'), join(dir, 'README.md'));
cpSync(join(root, 'LICENSE'), join(dir, 'LICENSE'));
writeFileSync(join(dir, 'package.json'), JSON.stringify({ ...main, version }, null, 2) + '\n');

if (flags.includes('--publish')) {
  let published = false;
  try {
    published = execFileSync('npm', ['view', `${main.name}@${version}`, 'version'], { stdio: ['ignore', 'pipe', 'ignore'] })
      .toString().trim() === version;
  } catch {}
  if (published) {
    console.log(`==> 公開済みなので飛ばす: ${main.name}@${version}`);
  } else {
    run('npm', ['publish', '--access', 'public', ...(process.env.GITHUB_ACTIONS ? ['--provenance'] : [])], { cwd: dir });
  }
} else if (flags.includes('--pack')) {
  run('npm', ['pack', '--pack-destination', out], { cwd: dir });
}
console.log(`==> 完了: ${out}`);
