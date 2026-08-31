declare module 'class-variance-authority' {
  import { ClassValue } from 'clsx';

  export type VariantProps<T> = T extends (props?: infer P) => any
    ? P extends Record<string, any>
      ? {
          [K in keyof P]?: P[K];
        }
      : {}
    : {};

  export interface VariantConfig<T extends Record<string, Record<string, any>> = {}> {
    variants?: T;
    defaultVariants?: {
      [K in keyof T]?: keyof T[K] | undefined;
    };
    compoundVariants?: Array<{
      [K in keyof T]?: keyof T[K] | undefined;
    } & {
      class?: ClassValue;
      className?: ClassValue;
    }>;
  }

  export function cva<T extends Record<string, Record<string, any>>>(
    base: ClassValue,
    config?: VariantConfig<T>
  ): (props?: {
    [K in keyof T]?: keyof T[K] | undefined;
  } & {
    className?: string;
    class?: ClassValue;
  }) => string;
}
