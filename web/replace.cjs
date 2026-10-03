const fs = require('fs');
let file = fs.readFileSync('components/AdminDashboard.tsx', 'utf8');

file = file.replace(/import \{ useEffect, useMemo, useState \} from 'react';/g, "import { useEffect, useMemo, useState } from 'react';\nimport toast from 'react-hot-toast';");

file = file.replace(/const \[status, setStatus\] = useState<\{ type: 'success' \| 'error'; message: string \} \| null>\(null\);\n/g, '');

file = file.replace(/setStatus\(null\);/g, '');

file = file.replace(/setStatus\(\{ type: 'success', message: (.*?) \}\);/g, 'toast.success($1);');

file = file.replace(/setStatus\(\{\s*type: 'error',\s*message: (.*?),\s*\}\);/gs, 'toast.error($1);');

file = file.replace(/\{status && \([\s\S]*?\{status\.message\}[\s\S]*?<\/div>[\s\S]*?\)\}/g, '');

fs.writeFileSync('components/AdminDashboard.tsx', file);
console.log('Done replacing in AdminDashboard.tsx');
