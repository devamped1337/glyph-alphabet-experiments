### receiver qwen7 (counted tasks ['t1|agent', 't1|mod', 't1|patient', 't1|pol', 't2|first', 't4|where', 't5|status']; overflow rows excluded: 0/67912)

| task | sender | glyph_id | prose | id_expanded | compact | recv_word_state | none | null_randorth* | null_shufpair* | samenorm_shuf* | raw_unsnapped |
|---|---|---|---|---|---|---|---|---|---|---|---|
| t1|agent | qwen7 | 0.832 | 0.980 | 0.980 | 0.832 | 0.832 | 0.164 | n/a(same model) | n/a(same model) | n/a(same model) | 0.832 |
| t1|agent | olmo7 | 0.832 | 0.980 | 0.980 | 0.832 | 0.832 | 0.164 | 0.124 | 0.044 | 0.140 | 0.832 |
| t1|mod | qwen7 | 0.992 | 1.000 | 1.000 | 0.480 | 0.996 | 0.504 | n/a(same model) | n/a(same model) | n/a(same model) | 0.996 |
| t1|mod | olmo7 | 0.992 | 1.000 | 1.000 | 0.480 | 0.996 | 0.504 | 0.192 | 0.724 | 0.504 | 0.988 |
| t1|patient | qwen7 | 0.784 | 0.916 | 0.916 | 0.808 | 0.788 | 0.156 | n/a(same model) | n/a(same model) | n/a(same model) | 0.788 |
| t1|patient | olmo7 | 0.784 | 0.916 | 0.916 | 0.808 | 0.788 | 0.156 | 0.092 | 0.068 | 0.108 | 0.780 |
| t1|pol | qwen7 | 0.984 | 1.000 | 1.000 | 1.000 | 0.992 | 0.504 | n/a(same model) | n/a(same model) | n/a(same model) | 0.992 |
| t1|pol | olmo7 | 0.984 | 1.000 | 1.000 | 1.000 | 0.992 | 0.504 | 0.508 | 0.496 | 0.532 | 0.984 |
| t2|first | qwen7 | 0.888 | 0.960 | 0.960 | 0.480 | 0.888 | 0.120 | n/a(same model) | n/a(same model) | n/a(same model) | 0.888 |
| t2|first | olmo7 | 0.888 | 0.960 | 0.960 | 0.480 | 0.888 | 0.120 | 0.204 | 0.112 | 0.124 | 0.884 |
| t4|where | qwen7 | 0.476 | 1.000 | 0.476 | 1.000 | 0.476 | 0.067 | n/a(same model) | n/a(same model) | n/a(same model) | 0.600 |
| t4|where | olmo7 | 0.476 | 1.000 | 0.476 | 1.000 | 0.476 | 0.067 | 0.029 | 0.124 | 0.071 | 0.514 |
| t5|status | qwen7 | 0.625 | 1.000 | 0.750 | 1.000 | 0.625 | 0.125 | n/a(same model) | n/a(same model) | n/a(same model) | 0.625 |
| t5|status | olmo7 | 0.625 | 1.000 | 0.750 | 1.000 | 0.625 | 0.125 | 0.125 | 0.125 | 0.125 | 0.635 |

| task | sender | glyph − prose | glyph − id_expanded | glyph − compact | glyph − recv_word_state |
|---|---|---|---|---|---|
| t1|agent | qwen7 | -0.148 [-0.215,-0.084] glyph worse | -0.148 [-0.215,-0.084] glyph worse | +0.000 [-0.080,+0.074] inconclusive | +0.000 [+0.000,+0.000] equivalent |
| t1|agent | olmo7 | -0.148 [-0.215,-0.084] glyph worse | -0.148 [-0.215,-0.084] glyph worse | +0.000 [-0.080,+0.074] inconclusive | +0.000 [+0.000,+0.000] equivalent |
| t1|mod | qwen7 | -0.008 [-0.020,+0.000] equivalent | -0.008 [-0.020,+0.000] equivalent | +0.512 [+0.477,+0.545] glyph better | -0.004 [-0.012,+0.000] equivalent |
| t1|mod | olmo7 | -0.008 [-0.020,+0.000] equivalent | -0.008 [-0.020,+0.000] equivalent | +0.512 [+0.477,+0.545] glyph better | -0.004 [-0.012,+0.000] equivalent |
| t1|patient | qwen7 | -0.132 [-0.204,-0.070] glyph worse | -0.132 [-0.204,-0.070] glyph worse | -0.024 [-0.106,+0.061] inconclusive | -0.004 [-0.012,+0.000] equivalent |
| t1|patient | olmo7 | -0.132 [-0.204,-0.070] glyph worse | -0.132 [-0.204,-0.070] glyph worse | -0.024 [-0.106,+0.061] inconclusive | -0.004 [-0.012,+0.000] equivalent |
| t1|pol | qwen7 | -0.016 [-0.033,-0.004] equivalent | -0.016 [-0.033,-0.004] equivalent | -0.016 [-0.033,-0.004] equivalent | -0.008 [-0.020,+0.000] equivalent |
| t1|pol | olmo7 | -0.016 [-0.033,-0.004] equivalent | -0.016 [-0.033,-0.004] equivalent | -0.016 [-0.033,-0.004] equivalent | -0.008 [-0.020,+0.000] equivalent |
| t2|first | qwen7 | -0.072 [-0.121,-0.030] glyph worse | -0.072 [-0.121,-0.030] glyph worse | +0.408 [+0.328,+0.483] glyph better | +0.000 [+0.000,+0.000] equivalent |
| t2|first | olmo7 | -0.072 [-0.121,-0.030] glyph worse | -0.072 [-0.121,-0.030] glyph worse | +0.408 [+0.328,+0.483] glyph better | +0.000 [+0.000,+0.000] equivalent |
| t4|where | qwen7 | -0.524 [-0.762,-0.305] glyph worse | +0.000 [+0.000,+0.000] equivalent | -0.524 [-0.762,-0.305] glyph worse | +0.000 [+0.000,+0.000] equivalent |
| t4|where | olmo7 | -0.524 [-0.757,-0.309] glyph worse | +0.000 [+0.000,+0.000] equivalent | -0.524 [-0.757,-0.309] glyph worse | +0.000 [+0.000,+0.000] equivalent |
| t5|status | qwen7 | -0.375 [-0.375,-0.375] glyph worse | -0.125 [-0.125,-0.125] glyph worse | -0.375 [-0.375,-0.375] glyph worse | +0.000 [+0.000,+0.000] equivalent |
| t5|status | olmo7 | -0.375 [-0.375,-0.375] glyph worse | -0.125 [-0.125,-0.125] glyph worse | -0.375 [-0.375,-0.375] glyph worse | +0.000 [+0.000,+0.000] equivalent |

| task | sender | LOO all | answer held out | other held out | none |
|---|---|---|---|---|---|
| t1|agent | qwen7 | 0.418 (500) | 0.000 (250) | 0.836 (250) | 0.164 |
| t1|agent | olmo7 | 0.424 (500) | 0.012 (250) | 0.836 (250) | 0.164 |
| t1|mod | qwen7 | 0.998 (500) | n/a | 0.998 (500) | 0.504 |
| t1|mod | olmo7 | 0.982 (500) | n/a | 0.982 (500) | 0.504 |
| t1|patient | qwen7 | 0.404 (500) | 0.000 (250) | 0.808 (250) | 0.156 |
| t1|patient | olmo7 | 0.404 (500) | 0.000 (250) | 0.808 (250) | 0.156 |
| t1|pol | qwen7 | 0.988 (500) | n/a | 0.988 (500) | 0.504 |
| t1|pol | olmo7 | 0.990 (500) | n/a | 0.990 (500) | 0.504 |
| t2|first | qwen7 | 0.450 (500) | 0.000 (250) | 0.900 (250) | 0.120 |
| t2|first | olmo7 | 0.458 (500) | 0.016 (250) | 0.900 (250) | 0.120 |
| t4|where | qwen7 | 0.133 (210) | 0.133 (210) | n/a | 0.067 |
| t4|where | olmo7 | 0.057 (210) | 0.057 (210) | n/a | 0.067 |
| t5|status | qwen7 | n/a | n/a | n/a | 0.125 |
| t5|status | olmo7 | n/a | n/a | n/a | 0.125 |

| task | glyph_id coverage (gold entry in final book, sender-independent) | cond acc among covered | e2e |
|---|---|---|---|
| t1|agent | 500/500 = 1.000 | 0.832 | 0.832 |
| t1|mod | 0/500 = 0.000 | nan | 0.992 |
| t1|patient | 500/500 = 1.000 | 0.784 | 0.784 |
| t1|pol | 0/500 = 0.000 | nan | 0.984 |
| t4|where | 224/420 = 0.533 | 0.893 | 0.476 |
| t5|status | 144/192 = 0.750 | 0.833 | 0.625 |

### receiver olmo7 (counted tasks ['t1|agent', 't1|patient', 't1|pol', 't4|where', 't5|status']; overflow rows excluded: 4914/45912)

| task | sender | glyph_id | prose | id_expanded | compact | recv_word_state | none | null_randorth* | null_shufpair* | samenorm_shuf* | raw_unsnapped |
|---|---|---|---|---|---|---|---|---|---|---|---|
| t1|agent | qwen7 | 0.836 | 0.992 | 0.992 | 0.320 | 0.836 | 0.164 | 0.124 | 0.048 | 0.112 | 0.776 |
| t1|agent | olmo7 | 0.836 | 0.992 | 0.992 | 0.320 | 0.836 | 0.164 | n/a(same model) | n/a(same model) | n/a(same model) | 0.836 |
| t1|patient | qwen7 | 0.804 | 0.976 | 0.976 | 0.876 | 0.796 | 0.132 | 0.120 | 0.060 | 0.116 | 0.784 |
| t1|patient | olmo7 | 0.804 | 0.976 | 0.976 | 0.876 | 0.796 | 0.132 | n/a(same model) | n/a(same model) | n/a(same model) | 0.796 |
| t1|pol | qwen7 | 0.876 | 0.956 | 0.956 | 1.000 | 0.844 | 0.492 | 0.492 | 0.492 | 0.496 | 0.876 |
| t1|pol | olmo7 | 0.876 | 0.956 | 0.956 | 1.000 | 0.844 | 0.492 | n/a(same model) | n/a(same model) | n/a(same model) | 0.844 |
| t4|where | qwen7 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.125 | 0.219 | 0.052 | 0.062 | 1.000 |
| t4|where | olmo7 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.125 | n/a(same model) | n/a(same model) | n/a(same model) | 1.000 |
| t5|status | qwen7 | 0.857 | 1.000 | 0.857 | 1.000 | 0.714 | 0.143 | 0.131 | 0.143 | 0.143 | 0.726 |
| t5|status | olmo7 | 0.857 | 1.000 | 0.857 | 1.000 | 0.714 | 0.143 | n/a(same model) | n/a(same model) | n/a(same model) | 0.857 |

| task | sender | glyph − prose | glyph − id_expanded | glyph − compact | glyph − recv_word_state |
|---|---|---|---|---|---|
| t1|agent | qwen7 | -0.156 [-0.228,-0.090] glyph worse | -0.156 [-0.228,-0.090] glyph worse | +0.516 [+0.410,+0.627] glyph better | +0.000 [+0.000,+0.000] equivalent |
| t1|agent | olmo7 | -0.156 [-0.228,-0.090] glyph worse | -0.156 [-0.228,-0.090] glyph worse | +0.516 [+0.410,+0.627] glyph better | +0.000 [+0.000,+0.000] equivalent |
| t1|patient | qwen7 | -0.172 [-0.254,-0.093] glyph worse | -0.172 [-0.254,-0.093] glyph worse | -0.072 [-0.172,+0.031] inconclusive | +0.008 [+0.000,+0.020] equivalent |
| t1|patient | olmo7 | -0.172 [-0.254,-0.093] glyph worse | -0.172 [-0.254,-0.093] glyph worse | -0.072 [-0.172,+0.031] inconclusive | +0.008 [+0.000,+0.020] equivalent |
| t1|pol | qwen7 | -0.080 [-0.124,-0.041] glyph worse | -0.080 [-0.124,-0.041] glyph worse | -0.124 [-0.174,-0.076] glyph worse | +0.032 [+0.004,+0.068] glyph better |
| t1|pol | olmo7 | -0.080 [-0.124,-0.041] glyph worse | -0.080 [-0.124,-0.041] glyph worse | -0.124 [-0.174,-0.076] glyph worse | +0.032 [+0.004,+0.068] glyph better |
| t4|where | qwen7 | +0.000 [+0.000,+0.000] equivalent | +0.000 [+0.000,+0.000] equivalent | +0.000 [+0.000,+0.000] equivalent | +0.000 [+0.000,+0.000] equivalent |
| t4|where | olmo7 | +0.000 [+0.000,+0.000] equivalent | +0.000 [+0.000,+0.000] equivalent | +0.000 [+0.000,+0.000] equivalent | +0.000 [+0.000,+0.000] equivalent |
| t5|status | qwen7 | -0.143 [-0.143,-0.143] glyph worse | +0.000 [+0.000,+0.000] equivalent | -0.143 [-0.143,-0.143] glyph worse | +0.143 [+0.143,+0.143] glyph better |
| t5|status | olmo7 | -0.143 [-0.143,-0.143] glyph worse | +0.000 [+0.000,+0.000] equivalent | -0.143 [-0.143,-0.143] glyph worse | +0.143 [+0.143,+0.143] glyph better |

| task | sender | LOO all | answer held out | other held out | none |
|---|---|---|---|---|---|
| t1|agent | qwen7 | 0.418 (500) | 0.000 (250) | 0.836 (250) | 0.164 |
| t1|agent | olmo7 | 0.418 (500) | 0.000 (250) | 0.836 (250) | 0.164 |
| t1|patient | qwen7 | 0.402 (500) | 0.000 (250) | 0.804 (250) | 0.132 |
| t1|patient | olmo7 | 0.404 (500) | 0.004 (250) | 0.804 (250) | 0.132 |
| t1|pol | qwen7 | 0.932 (500) | n/a | 0.932 (500) | 0.492 |
| t1|pol | olmo7 | 0.894 (500) | n/a | 0.894 (500) | 0.492 |
| t4|where | qwen7 | 0.125 (96) | 0.125 (96) | n/a | 0.125 |
| t4|where | olmo7 | 0.010 (96) | 0.010 (96) | n/a | 0.125 |
| t5|status | qwen7 | n/a | n/a | n/a | 0.143 |
| t5|status | olmo7 | n/a | n/a | n/a | 0.143 |

| task | glyph_id coverage (gold entry in final book, sender-independent) | cond acc among covered | e2e |
|---|---|---|---|
| t1|agent | 500/500 = 1.000 | 0.836 | 0.836 |
| t1|patient | 500/500 = 1.000 | 0.804 | 0.804 |
| t1|pol | 0/500 = 0.000 | nan | 0.876 |
| t4|where | 192/192 = 1.000 | 1.000 | 1.000 |
| t5|status | 144/168 = 0.857 | 1.000 | 0.857 |

### DEV glyph_id by depth (li 0=emb), counted tasks

| receiver | li=0 | li=1 | li=2 |
|---|---|---|---|
| qwen7 | 0.874 (n=508) | 0.756 (n=508) | 0.744 (n=508) |
| olmo7 | 0.816 (n=348) | 0.592 (n=348) | 0.552 (n=348) |