import { mkdir, copyFile } from "node:fs/promises";

await mkdir(new URL("../dist/", import.meta.url), { recursive: true });
await copyFile(new URL("../src/index.js", import.meta.url), new URL("../dist/index.js", import.meta.url));
await copyFile(new URL("../src/index.js", import.meta.url), new URL("../dist/index.cjs", import.meta.url));
await copyFile(new URL("../src/index.d.ts", import.meta.url), new URL("../dist/index.d.ts", import.meta.url));
