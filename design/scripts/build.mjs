import {cp,mkdir,rm} from 'node:fs/promises';
import {resolve} from 'node:path';
const root=resolve(import.meta.dirname,'..');
await rm(resolve(root,'dist'),{recursive:true,force:true});
await mkdir(resolve(root,'dist'));
for(const file of ['index.html','pages','components','assets','css','js','data','theme','specs'])await cp(resolve(root,file),resolve(root,'dist',file),{recursive:true});
console.log('Built portable static HTML kit in dist/. Serve with any static HTTP server.');
