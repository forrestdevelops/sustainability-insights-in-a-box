# Copyright 2024 Cisco Systems, Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

from cryptography.fernet import Fernet

def encrypt(secret):
  """
  Encrypts given secrets, generates encryption key
  Parameters:
      secret: text like device password to be encrypted
  Returns:
      encrypted: encrypted secret
      key: encryption key, required to decrypt
  """
  if secret is None:
      return None
      
  key = Fernet.generate_key()
  fernet = Fernet(key)
  encrypted = fernet.encrypt(secret.encode())
  return (encrypted.decode(), key.decode())

def decrypt(secret, key):
  """
  Decrypts given secret, generates encryption key
  Parameters:
      secret: secret to be decrypted
      key: secret's encryption key
  Returns:
      decrypted secret (DO NOT log decrypted secrets)
      None on failure to decrypt say due to invalid key
  """
  if secret is None or key is None:
     return None
    
  fernet = Fernet(key)
  try:
      decrypted = fernet.decrypt(secret.encode()).decode()
  except:
      return None
  return decrypted

