declare module '@radix-ui/react-label' {
  import * as React from 'react';

  export interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
    asChild?: boolean;
  }

  export const Root: React.ForwardRefExoticComponent<
    LabelProps & React.RefAttributes<HTMLLabelElement>
  > & {
    displayName?: string;
  };
}
