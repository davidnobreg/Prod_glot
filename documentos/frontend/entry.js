// Fonte do bundle TipTap vendorizado (Fase 7).
// NÃO é servido diretamente — gere o bundle e copie para
// static/documentos/js/vendor/tiptap.bundle.min.js (ver README.md).
// Build: npx esbuild entry.js --bundle --minify --format=iife --outfile=tiptap.bundle.min.js
import { Editor, Node, mergeAttributes } from '@tiptap/core'
import { StarterKit } from '@tiptap/starter-kit'
import { TextAlign } from '@tiptap/extension-text-align'
import { Table, TableRow, TableCell, TableHeader } from '@tiptap/extension-table'
import { TextStyle } from '@tiptap/extension-text-style'
import { Color } from '@tiptap/extension-color'
import { Highlight } from '@tiptap/extension-highlight'
import { Subscript } from '@tiptap/extension-subscript'
import { Superscript } from '@tiptap/extension-superscript'
import { PaginationPlus } from 'tiptap-pagination-plus'

// Underline NÃO é importado aqui: StarterKit v3 já o inclui (evita
// "Duplicate extension names found: ['underline']").
window.TipTapBundle = {
  Editor, Node, mergeAttributes, StarterKit,
  TextAlign, Table, TableRow, TableCell, TableHeader,
  TextStyle, Color, Highlight, Subscript, Superscript,
  PaginationPlus,
}
