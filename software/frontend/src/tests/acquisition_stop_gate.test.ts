import assert from 'node:assert/strict';
import { AcquisitionStopGate } from '../api/acquisitionStopGate';

const gate = new AcquisitionStopGate();
assert.equal(gate.tryBegin(), true, 'first STOP request should acquire the gate');
assert.equal(gate.tryBegin(), false, 'automatic/manual duplicate should be ignored');
gate.finish();
assert.equal(gate.tryBegin(), true, 'a later STOP attempt should be allowed');
gate.finish();

console.log('acquisition stop gate regression checks passed');
