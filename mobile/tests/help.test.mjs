import {test} from 'node:test';
import assert from 'node:assert/strict';
import {apiPath,helpDestination} from '../src/policy.mjs';
test('help is consultation-only and preserves all companion restrictions',()=>{
 assert.equal(apiPath('/help/ask','POST'),'/api/v1/help/ask');
 for(const method of ['GET','PATCH','DELETE'])assert.throws(()=>apiPath('/help/ask',method));
 for(const path of ['/help/admin','/help/ask/../../admin','/simulations/new','/documents/id/process','/admin/users'])assert.throws(()=>apiPath(path,'POST'));
});
test('help navigation accepts only known mobile sections or fixed public web procedures',()=>{
 assert.deepEqual(helpDestination('/documents'),{web:false,section:'documents'});
 assert.deepEqual(helpDestination('/mobile/account'),{web:false,section:'account'});
 assert.deepEqual(helpDestination('/forgot-password'),{web:true,section:''});
 for(const value of ['https://evil.example','//evil.example','/admin/users','/documents/../../admin','javascript:alert(1)','/forgot-password?token=secret',null,undefined])assert.equal(helpDestination(value),null);
});

test('server origin is build-time HTTPS configuration without embedded paths or credentials',async()=>{
 const {serverOrigin}=await import('../src/policy.mjs');
 assert.equal(serverOrigin('https://socratia.example/'),'https://socratia.example');
 for(const value of ['http://socratia.example','https://user:pass@socratia.example','https://socratia.example/api','https://socratia.example/?token=secret','javascript:alert(1)'])assert.throws(()=>serverOrigin(value));
});
