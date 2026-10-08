import { createElement } from "react";
import { SHARED_CLASS } from "./constants";

const className = 'text-accent font-semibold'
const BASE = 'base-token'

export const a = createElement('span', { className }, label)
export const b = createElement('span', { className: 'p-4 flex' }, label)
export const c = createElement('a', { className: 'sr-only focus:z-skiplink' +
  ' focus:outline-accent-orange' }, 'Skip to content')
export const d = createElement('a', { className: BASE + ' extra-token' }, label)
export const e = createElement('a', { className: 'static-token' + dynamicFn() }, l)
export const f = createElement('span', getProps(), label)
export const g = React.cloneElement(el, { className: 'bg-red-500' })
export const h = createElement('b', { className: SHARED_CLASS }, label)
