import * as esbuild from "esbuild";
import fs from "node:fs/promises";

const sqlPlugin = {
  name: "sql-loader",
  setup(build) {
    build.onLoad({ filter: /\.sql$/ }, async (args) => {
      const text = await fs.readFile(args.path, "utf8");
      return { contents: `export default ${JSON.stringify(text)};`, loader: "js" };
    });
  },
};

await esbuild.build({
  entryPoints: ["src/index.js"],
  bundle: true,
  format: "esm",
  platform: "neutral",
  target: "es2022",
  outfile: "dist/worker.js",
  minify: false,
  sourcemap: false,
  plugins: [sqlPlugin],
});

const stats = await fs.stat("dist/worker.js");
console.log(`Built dist/worker.js (${stats.size} bytes)`);
// ak:77343581a6d484b5
