import assert from 'node:assert/strict';
import { g1ResultLabel } from '../components/DeviceView';

const complete = {session_state: 'COMPLETE', is_simulated: false};
const physical = {conclusion: 'PHYSICAL_G1_PASSED', verification_result: 'PASS' as const, is_simulated: false};
assert.equal(g1ResultLabel(complete, physical), 'G1 PASSED — PHYSICAL USB');
assert.match(g1ResultLabel({...complete, is_simulated: true}, physical)!, /SOFTWARE SIMULATION/);
assert.match(g1ResultLabel(complete, {...physical, is_simulated: true})!, /PHYSICAL G1 PENDING/);
assert.match(g1ResultLabel(complete, {...physical, verification_result: 'FAIL'})!, /FAILED/);
assert.equal(g1ResultLabel({...complete, session_state: 'STREAMING'}, physical), null);
assert.equal(g1ResultLabel(null, physical), null);
assert.equal(g1ResultLabel(complete, {...physical, conclusion: 'UNVERIFIED'}), null);
console.log('Device G1 status provenance: passed');
