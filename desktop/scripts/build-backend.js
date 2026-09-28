// Freezes the Python backend into desktop/build/backend/chatplays-backend.
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const desktopDir = path.join(__dirname, "..");
const repoRoot = path.join(desktopDir, "..");
const venvDir = path.join(repoRoot, ".build-venv");
const venvPython = path.join(venvDir, "Scripts", "python.exe");

const distPath = path.join(desktopDir, "build", "backend");
const workPath = path.join(desktopDir, "build", "pyinstaller-work");

// Folders here can carry the Windows read-only flag, which makes PyInstaller's
// own cleanup fail with "Access is denied", so clear and remove them first.
function removeTree(dir) {
  if (!fs.existsSync(dir)) return;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const entryPath = path.join(dir, entry.name);
    if (entry.isDirectory()) removeTree(entryPath);
    else fs.chmodSync(entryPath, 0o666);
  }
  fs.chmodSync(dir, 0o777);
  fs.rmSync(dir, { recursive: true, force: true });
}

function run(command, args) {
  console.log(`> ${command} ${args.join(" ")}`);
  execFileSync(command, args, { stdio: "inherit", cwd: repoRoot });
}

if (process.platform !== "win32") {
  console.error("The backend build currently targets Windows only (vgamepad needs ViGEmBus).");
  process.exit(1);
}

// A python.org interpreter, not the MSYS one the dev venv uses: PyInstaller
// only supports standard CPython builds reliably.
if (!fs.existsSync(venvPython)) {
  run("py", ["-3.12", "-m", "venv", venvDir]);
}

run(venvPython, ["-m", "pip", "install", "--disable-pip-version-check", "-q",
  "-r", path.join(repoRoot, "requirements.txt"), "pyinstaller"]);

removeTree(distPath);
removeTree(workPath);

run(venvPython, [
  "-m", "PyInstaller",
  "--noconfirm",
  "--clean",
  "--distpath", distPath,
  "--workpath", workPath,
  path.join(repoRoot, "packaging", "chatplays-backend.spec"),
]);
