// this is crunk's comment, with an unmatched apostrophe
export const ERROR_TEXT_CLASS = 'rounded-4 bg-red-500 text-white';
export const FOCUS_RING = "outline outline-2 outline-offset-2";
export const GREETING = "Hello, world!";
export const BG = "bg-[#123456]";
export const CLS = `flex gap-2 ${extra} outline outline-2`;
export const LONE = `bg-red-500 ${extra}`;
export const VARIANTS = "md:hidden lg:flex items-center";
export const SHARED_CLASS = "text-accent font-semibold";
export const badgeVariants = cva('inline-flex items-center', {
  variants: {
    intent: {
      primary: 'bg-blue-500 text-white',
      danger: 'bg-red-500 text-white',
    },
  },
});
export const classes = twMerge('p-4 flex', 'gap-2 items-center');
