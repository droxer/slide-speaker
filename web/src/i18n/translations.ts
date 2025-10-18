import type {Locale} from './config';
import {locales as availableLocales} from './config';
import en from './messages/en.json';
import zhCN from './messages/zh-CN.json';
import zhTW from './messages/zh-TW.json';
import ja from './messages/ja.json';
import ko from './messages/ko.json';
import th from './messages/th.json';

export type Messages = {[key: string]: string | Messages};

const localeMessages = {
  en,
  'zh-CN': zhCN,
  'zh-TW': zhTW,
  ja,
  ko,
  th
} satisfies Record<Locale, Messages>;

export const translations: Record<Locale, Messages> = localeMessages;

export {availableLocales};
