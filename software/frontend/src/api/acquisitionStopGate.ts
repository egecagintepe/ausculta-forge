/** Prevent concurrent manual and automatic STOP requests for one acquisition. */
export class AcquisitionStopGate {
  private inFlight = false;

  public tryBegin(): boolean {
    if (this.inFlight) return false;
    this.inFlight = true;
    return true;
  }

  public finish(): void {
    this.inFlight = false;
  }
}
