// Freezes the Python backend into desktop/build/backend/chatplays-backend.
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const desktopDir = path.join(__dirname, "..");
const repoRoot = path.join(desktopDir, "..");
const venvDir = path.join(repoRoot, ".build-venv");
const venvPython = path.join(venvDir, "Scripts", "python.exe");

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

run(venvPython, [
  "-m", "PyInstaller",
  "--noconfirm",
  "--clean",
  "--distpath", path.join(desktopDir, "build", "backend"),
  "--workpath", path.join(desktopDir, "build", "pyinstaller-work"),
  path.join(repoRoot, "packaging", "chatplays-backend.spec"),
]);
