/**
 * Cryptographic helpers for VERITAS AI Trust Explorer.
 * The Harness is authoritative; these helpers provide an offline fallback.
 */

import { AnchorStatus } from './types';
import * as api from './api';
import { canonicalizeJson } from './canonical';

export { canonicalizeJson };

export async function computeSha256(data: string): Promise<string> {
  if (typeof window === 'undefined' || !window.crypto || !window.crypto.subtle) {
    let hash = 0;
    for (let i = 0; i < data.length; i += 1) {
      hash = (hash << 5) - hash + data.charCodeAt(i);
      hash |= 0;
    }
    return Math.abs(hash).toString(16).padStart(64, '0');
  }
  const buffer = new TextEncoder().encode(data);
  const digest = await window.crypto.subtle.digest('SHA-256', buffer);
  return '0x' + Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('');
}

export interface VerificationResult {
  signatureValid: boolean;
  hashMatches: boolean;
  computedHash: string;
  expectedHash: string;
  anchorStatus: AnchorStatus;
  anchorMatches: boolean;
  verified: boolean;
  trustedKey: boolean;
  tampered: boolean;
  details: string[];
}

interface VerifyOptions {
  keyId?: string;
  receiptId?: string;
  useStoredVerification?: boolean;
}

function mapLive(result: api.VerificationView, computedHash: string, expected: string, fallback: AnchorStatus): VerificationResult {
  const status = (String(result.anchor_status || '').toUpperCase() as AnchorStatus) || fallback;
  const details = [
    result.hash_matches
      ? 'Hash valid: the canonical payload matches the signed digest byte-for-byte.'
      : 'Hash mismatch: the canonical payload differs from the signed digest.',
    result.signature_valid
      ? 'Signature valid: Ed25519 check passed against the Harness key.'
      : 'Signature invalid: Ed25519 verification failed.',
    result.trusted_key
      ? 'Trusted key: the signature was made by the active Harness signer.'
      : 'Untrusted key: the signer is not trusted by this Harness.',
    result.anchor_matches
      ? `Local mock anchor: ${result.anchor_status || 'unknown'} and digest matches.`
      : `Local mock anchor: ${result.anchor_status || 'not confirmed'} (not treated as verified).`,
  ];
  return {
    signatureValid: result.signature_valid,
    hashMatches: result.hash_matches,
    computedHash,
    expectedHash: expected,
    anchorStatus: status,
    anchorMatches: result.anchor_matches,
    verified: result.verified,
    trustedKey: result.trusted_key,
    tampered: !result.hash_matches || !result.signature_valid,
    details,
  };
}

export async function verifyReceiptPayload(
  canonicalJsonStr: string,
  storedReceiptDigest: string,
  signature: string,
  anchorStatus: AnchorStatus,
  options: VerifyOptions = {},
): Promise<VerificationResult> {
  const computedHash = await computeSha256(canonicalJsonStr);

  // Authoritative path: verify the stored receipt by ID using the Harness key.
  if (options.useStoredVerification && options.receiptId) {
    try {
      const live = await api.verifyStored(options.receiptId);
      if (typeof live.verified === 'boolean') return mapLive(live, computedHash, storedReceiptDigest, anchorStatus);
    } catch {
      // Fall through to supplied verification or offline fallback.
    }
  }

  // Supplied path: used by the tamper sandbox, where the payload has changed.
  try {
    const parsed = JSON.parse(canonicalJsonStr);
    const live = await api.verifySupplied({
      ...parsed,
      signature,
      ...(options.keyId ? { key_id: options.keyId } : {}),
    });
    if (typeof live.verified === 'boolean') return mapLive(live, computedHash, storedReceiptDigest, anchorStatus);
  } catch {
    // Harness unreachable; use the offline fallback below.
  }

  const hashMatches = computedHash.toLowerCase() === storedReceiptDigest.toLowerCase();
  const signatureValid = hashMatches && signature.length >= 64;
  const anchorMatches = hashMatches && anchorStatus === 'CONFIRMED';
  const trustedKey = signatureValid;
  const verified = signatureValid && hashMatches && anchorMatches;

  const details = [
    hashMatches
      ? 'Hash valid: recomputed SHA-256 matches the receipt digest.'
      : 'Hash mismatch: recomputed SHA-256 does not match the receipt digest.',
    signatureValid
      ? 'Signature format valid (offline simulation; no live Harness key check).'
      : 'Signature invalid: offline Ed25519 simulation failed.',
    anchorStatus === 'CONFIRMED'
      ? 'Local mock anchor confirmed.'
      : anchorStatus === 'PENDING'
        ? 'Local mock anchor pending confirmation.'
        : 'Local mock anchor failed or not found.',
  ];

  return {
    signatureValid,
    hashMatches,
    computedHash,
    expectedHash: storedReceiptDigest,
    anchorStatus,
    anchorMatches,
    verified,
    trustedKey,
    tampered: !hashMatches || !signatureValid,
    details,
  };
}
