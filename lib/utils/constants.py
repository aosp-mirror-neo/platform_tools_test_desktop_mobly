# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

HTML_GRAPH_TEMPLATE="""
    <html>
      <head>
         <script language="javascript" type="text/javascript" src="https://graphviz.corp.google.com/js"></script>
      </head>
      <body>
         <!-- Create a 'script' element with 'type="text/dot"' and class equal to the layout -->
         <!-- engine to use: dot, neato, fdp, sfdp, twopi, or circo -->
         <script type="text/dot" class="dot" format="svg">
            digraph {content}
         </script>
      </body>
    </html>
"""
