"""
Symbol mappings for LaTeX to Unicode conversion.
Contains mathematical, chemical, and other special symbols.
"""

# Mathematical Operators
MATH_OPERATORS = {
    '\\times': '×',
    '\\div': '÷',
    '\\pm': '±',
    '\\cdot': '·',
    '\\bullet': '•',
    '\\circ': '∘',
    '\\oplus': '⊕',
    '\\otimes': '⊗',
    '\\dotplus': '∔',
    '\\divideontimes': '⋇'
}

# Arrows and Relations
ARROWS = {
    '\\rightarrow': '→',
    '\\leftarrow': '←',
    '\\Rightarrow': '⇒',
    '\\Leftarrow': '⇐',
    '\\leftrightarrow': '↔',
    '\\Leftrightarrow': '⇔',
    '\\longrightarrow': '⟶',
    '\\longleftarrow': '⟵',
    '\\rightleftharpoons': '⇌',
    '\\uparrow': '↑',
    '\\downarrow': '↓',
    '\\updownarrow': '↕',
    '\\Uparrow': '⇑',
    '\\Downarrow': '⇓',
    '\\Updownarrow': '⇕',
    '\\mapsto': '↦',
    '\\longmapsto': '⟼',
    '\\hookrightarrow': '↪',
    '\\hookleftarrow': '↩',
    '\\dashrightarrow': '⇢',
    '\\dashleftarrow': '⇠',
    '\\rightsquigarrow': '⇝',
    '\\leftrightsquigarrow': '↭'
}

# Greek Letters
GREEK_LETTERS = {
    '\\alpha': 'α',
    '\\beta': 'β',
    '\\gamma': 'γ',
    '\\delta': 'δ',
    '\\Delta': 'Δ',
    '\\theta': 'θ',
    '\\Theta': 'Θ',
    '\\lambda': 'λ',
    '\\Lambda': 'Λ',
    '\\mu': 'μ',
    '\\pi': 'π',
    '\\Pi': 'Π',
    '\\sigma': 'σ',
    '\\Sigma': 'Σ',
    '\\omega': 'ω',
    '\\Omega': 'Ω',
    '\\epsilon': 'ε',
    '\\varepsilon': 'ε',
    '\\zeta': 'ζ',
    '\\eta': 'η',
    '\\iota': 'ι',
    '\\kappa': 'κ',
    '\\nu': 'ν',
    '\\xi': 'ξ',
    '\\Xi': 'Ξ',
    '\\rho': 'ρ',
    '\\tau': 'τ',
    '\\phi': 'φ',
    '\\Phi': 'Φ',
    '\\chi': 'χ',
    '\\psi': 'ψ',
    '\\Psi': 'Ψ'
}

# Chemical Bonds and Structures
CHEMICAL_BONDS = {
    '\\bond': '−',
    '\\doublebond': '═',
    '\\triplebond': '≡',
    '\\wedge': '⫽',
    '\\dash': '⫻',
    '\\wavy': '⌇',
    '\\benzene': '⌬',
    '\\phenyl': 'Ph',
    '\\aromatic': '⬡',
    '\\ring': '○',
    '\\delocalized': '⟷',
    '\\coordbond': '→',
    '\\dative': '→'
}

# Chemical States and Charges
CHEMICAL_STATES = {
    '\\ce': '',
    '\\state': '',
    '\\aq': '(aq)',
    '\\s': '(s)',
    '\\l': '(l)',
    '\\g': '(g)',
    '\\positive': '⊕',
    '\\negative': '⊖',
    '\\delta+': 'δ⁺',
    '\\delta-': 'δ⁻',
    '\\electron': 'e⁻',
    '\\radical': '•'
}

# Stereochemistry
STEREOCHEMISTRY = {
    '\\cis': 'cis-',
    '\\trans': 'trans-',
    '\\racemic': '(±)',
    '\\meso': 'meso-',
    '\\RR': '(R,R)-',
    '\\SS': '(S,S)-',
    '\\RS': '(R,S)-',
    '\\SR': '(S,R)-',
    '\\R': '(R)-',
    '\\S': '(S)-',
    '\\Z': '(Z)-',
    '\\E': '(E)-',
    '\\syn': 'syn-',
    '\\anti': 'anti-'
}

# Conformations
CONFORMATIONS = {
    '\\chair': '⌘',
    '\\boat': '⎈',
    '\\twist': '⌅'
}

# Trigonometric Functions
TRIG_FUNCTIONS = {
    '\\sin': 'sin',
    '\\cos': 'cos',
    '\\tan': 'tan',
    '\\cot': 'cot',
    '\\sec': 'sec',
    '\\csc': 'csc',
    '\\arcsin': 'sin⁻¹',
    '\\arccos': 'cos⁻¹',
    '\\arctan': 'tan⁻¹',
    '\\arccot': 'cot⁻¹',
    '\\arcsec': 'sec⁻¹',
    '\\arccsc': 'csc⁻¹'
}

# Set Theory
SET_THEORY = {
    '\\subset': '⊂',
    '\\supset': '⊃',
    '\\subseteq': '⊆',
    '\\supseteq': '⊇',
    '\\cup': '∪',
    '\\cap': '∩',
    '\\in': '∈',
    '\\notin': '∉',
    '\\emptyset': '∅',
    '\\varnothing': '∅',
    '\\setminus': '∖',
    '\\smallsetminus': '∖',
    '\\subsetneq': '⊊',
    '\\supsetneq': '⊋',
    '\\nsubseteq': '⊈',
    '\\nsupseteq': '⊉'
}

# Calculus and Analysis
CALCULUS = {
    '\\nabla': '∇',
    '\\partial': '∂',
    '\\sum': '∑',
    '\\prod': '∏',
    '\\int': '∫',
    '\\iint': '∬',
    '\\iiint': '∭',
    '\\oint': '∮',
    '\\oiint': '∯',
    '\\oiiint': '∰'
}

# Logic Symbols
LOGIC = {
    '\\neg': '¬',
    '\\lnot': '¬',
    '\\land': '∧',
    '\\lor': '∨',
    '\\implies': '⟹',
    '\\forall': '∀',
    '\\exists': '∃',
    '\\nexists': '∄'
}

# Comparison Operators
COMPARISONS = {
    '\\approx': '≈',
    '\\neq': '≠',
    '\\equiv': '≡',
    '\\leq': '≤',
    '\\geq': '≥',
    '\\ll': '≪',
    '\\gg': '≫'
}

# Matrix Box Drawing Characters
MATRIX_BOX = {
    '\\matrix': '⎡',
    '\\endmatrix': '⎦',
    '\\left[': '⎡',
    '\\right]': '⎦',
    '\\left|': '|',
    '\\right|': '|',
    '\\hline': '-',
    '\\vline': '|',
    '\\top': '⎡',
    '\\bottom': '⎦',
    '\\left': '|',
    '\\right': '|',
    '\\middle': '|',
    '\\begin{matrix}': '⎡',
    '\\end{matrix}': '⎦',
    '\\begin{pmatrix}': '⎡',
    '\\end{pmatrix}': '⎦',
    '\\begin{bmatrix}': '⎡',
    '\\end{bmatrix}': '⎦'
}

# Merge all dictionaries into one
ALL_SYMBOLS = {}
ALL_SYMBOLS.update(MATH_OPERATORS)
ALL_SYMBOLS.update(ARROWS)
ALL_SYMBOLS.update(GREEK_LETTERS)
ALL_SYMBOLS.update(CHEMICAL_BONDS)
ALL_SYMBOLS.update(CHEMICAL_STATES)
ALL_SYMBOLS.update(STEREOCHEMISTRY)
ALL_SYMBOLS.update(CONFORMATIONS)
ALL_SYMBOLS.update(TRIG_FUNCTIONS)
ALL_SYMBOLS.update(SET_THEORY)
ALL_SYMBOLS.update(CALCULUS)
ALL_SYMBOLS.update(LOGIC)
ALL_SYMBOLS.update(COMPARISONS)
ALL_SYMBOLS.update(MATRIX_BOX) 