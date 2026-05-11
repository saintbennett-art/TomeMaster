declare module 'nspell' {
  interface NSpell {
    correct(word: string): boolean;
    suggest(word: string): string[];
    add(word: string): void;
    remove(word: string): void;
  }
  export default function nspell(aff: string | object, dic?: string | object): NSpell;
}
