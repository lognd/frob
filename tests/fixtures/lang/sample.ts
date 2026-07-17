/** Adds two numbers. */
export function add(x: number, y: number): number {
  // sum them
  return x + y;
}

export class Widget {
  private count: number;

  /** Renders the widget. */
  public render(label: string): string {
    return label;
  }

  private hidden(): void {}
}

export const MAX_WIDGETS = 10;

export interface Shape {
  area(): number;
}
