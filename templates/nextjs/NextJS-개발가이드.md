# CLAUDE.md - Next.js 프로젝트 상세 가이드

> 이 문서는 Claude Code가 Next.js 프로젝트에서 바이브코딩 시 참조하는 종합 가이드입니다. 모든 코드 예시는 실무에서 바로 복사하여 사용할 수 있는 완전한 형태입니다.

---

## 1. 프로젝트 개요

### 기술 스택

| 기술 | 버전 | 용도 |
| --- | --- | --- |
| Next.js | 14.2+ | 풀스택 React 프레임워크 |
| React | 18.3+ | UI 라이브러리 |
| TypeScript | 5.4+ | 타입 안전성 |
| Tailwind CSS | 3.4+ | 유틸리티 퍼스트 스타일링 |
| ESLint | 8.x | 코드 린팅 |
| Prettier | 3.x | 코드 포매팅 |
| Zod | 3.23+ | 런타임 스키마 검증 |
| NextAuth.js (Auth.js) | 5.x | 인증 |
| Prisma / Drizzle | 최신 | ORM / 데이터베이스 |
| Jest | 29.x | 단위 테스트 |
| Playwright | 1.44+ | E2E 테스트 |

### 프로젝트 구조 상세 트리

```
project-root/
├── app/                          # App Router 루트
│   ├── (auth)/                   # Route Group: 인증 관련
│   │   ├── login/
│   │   │   └── page.tsx
│   │   ├── register/
│   │   │   └── page.tsx
│   │   └── layout.tsx            # 인증 페이지 전용 레이아웃
│   ├── (dashboard)/              # Route Group: 대시보드
│   │   ├── dashboard/
│   │   │   ├── page.tsx
│   │   │   ├── loading.tsx
│   │   │   └── error.tsx
│   │   ├── settings/
│   │   │   └── page.tsx
│   │   └── layout.tsx            # 대시보드 전용 레이아웃 (사이드바 등)
│   ├── (marketing)/              # Route Group: 마케팅/공개 페이지
│   │   ├── page.tsx              # 홈페이지
│   │   ├── about/
│   │   │   └── page.tsx
│   │   └── layout.tsx
│   ├── api/                      # Route Handlers
│   │   ├── auth/[...nextauth]/
│   │   │   └── route.ts
│   │   ├── webhooks/
│   │   │   └── route.ts
│   │   └── upload/
│   │       └── route.ts
│   ├── layout.tsx                # 루트 레이아웃
│   ├── not-found.tsx             # 전역 404
│   ├── error.tsx                 # 전역 에러 바운더리
│   ├── global-error.tsx          # 루트 레이아웃 에러 바운더리
│   └── globals.css               # 전역 스타일
├── components/
│   ├── ui/                       # 범용 UI 컴포넌트
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── modal.tsx
│   │   ├── skeleton.tsx
│   │   └── toast.tsx
│   ├── features/                 # 도메인별 컴포넌트
│   │   ├── auth/
│   │   │   ├── login-form.tsx
│   │   │   └── user-avatar.tsx
│   │   └── posts/
│   │       ├── post-card.tsx
│   │       └── post-list.tsx
│   └── layout/                   # 레이아웃 컴포넌트
│       ├── header.tsx
│       ├── footer.tsx
│       └── sidebar.tsx
├── lib/                          # 유틸리티 및 설정
│   ├── auth.ts                   # NextAuth 설정
│   ├── db.ts                     # DB 연결
│   ├── utils.ts                  # 공통 유틸리티 (cn 함수 등)
│   └── validations.ts            # Zod 스키마 모음
├── actions/                      # Server Actions
│   ├── auth-actions.ts
│   ├── post-actions.ts
│   └── user-actions.ts
├── types/                        # TypeScript 타입 정의
│   ├── index.ts
│   └── database.ts
├── hooks/                        # 커스텀 React Hooks
│   ├── use-debounce.ts
│   └── use-media-query.ts
├── constants/                    # 상수 값
│   └── index.ts
├── public/                       # 정적 파일
│   ├── images/
│   └── fonts/
├── prisma/                       # Prisma 스키마 (ORM 사용 시)
│   └── schema.prisma
├── middleware.ts                  # Next.js Middleware
├── next.config.js                # Next.js 설정
├── tsconfig.json                 # TypeScript 설정
├── tailwind.config.ts            # Tailwind CSS 설정
├── .env.local                    # 로컬 환경변수 (gitignore)
├── .env.example                  # 환경변수 템플릿
└── .eslintrc.json                # ESLint 설정
```

### next.config.js 핵심 설정

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // 이미지 최적화: 외부 도메인 허용
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'example.com',
        pathname: '/images/**',
      },
    ],
  },
  // 보안 헤더
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-XSS-Protection', value: '1; mode=block' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
        ],
      },
    ];
  },
  // 실험적 기능
  experimental: {
    typedRoutes: true,      // 타입 안전 라우트
    serverActions: {
      bodySizeLimit: '2mb',  // Server Action 바디 크기 제한
    },
  },
};

module.exports = nextConfig;
```

### tsconfig.json 핵심 설정

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "forceConsistentCasingInFileNames": true,
    "moduleResolution": "bundler",
    "paths": {
      "@/*": ["./*"]
    },
    "plugins": [{ "name": "next" }]
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

### 환경 구분

| 환경 | 파일 | 용도 |
| --- | --- | --- |
| 공통 | `.env` | 모든 환경 공통 기본값 |
| 로컬 개발 | `.env.local` | 개인 개발 환경 (gitignore) |
| 개발 | `.env.development` | development 환경 |
| 스테이징 | `.env.staging` | staging 배포 환경 |
| 프로덕션 | `.env.production` | production 배포 환경 |

우선순위: `.env.local` &gt; `.env.[환경]` &gt; `.env`

---

## 2. 코딩 컨벤션

### 네이밍 규칙

#### 파일 및 디렉토리

```
# 컴포넌트 파일: kebab-case
components/ui/button.tsx
components/features/auth/login-form.tsx
components/features/posts/post-card.tsx

# 라우트 파일: Next.js 컨벤션 고정
app/page.tsx
app/layout.tsx
app/loading.tsx
app/error.tsx
app/not-found.tsx
app/template.tsx
app/api/users/route.ts

# Server Actions 파일: kebab-case + 접미사 -actions
actions/auth-actions.ts
actions/post-actions.ts

# 유틸리티 파일: kebab-case
lib/format-date.ts
lib/api-client.ts

# 훅 파일: kebab-case, use- 접두사
hooks/use-debounce.ts
hooks/use-media-query.ts

# 타입 파일: kebab-case
types/database.ts
types/api-responses.ts

# 상수 파일: kebab-case
constants/routes.ts
constants/config.ts
```

#### 변수, 함수, 컴포넌트, 타입

```typescript
// 컴포넌트: PascalCase
export function UserProfile({ user }: UserProfileProps) {}
export default function DashboardPage() {}

// 함수: camelCase, 동사로 시작
function getUserById(id: string) {}
function formatCurrency(amount: number) {}
function validateEmail(email: string) {}
async function fetchPosts() {}

// 변수: camelCase
const isLoading = true;
const userName = 'John';
const postCount = 42;

// 불리언 변수: is/has/can/should 접두사
const isAuthenticated = true;
const hasPermission = false;
const canEdit = true;
const shouldRedirect = false;

// 상수: UPPER_SNAKE_CASE
const MAX_RETRY_COUNT = 3;
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;
const DEFAULT_PAGE_SIZE = 20;
const CACHE_TTL_SECONDS = 3600;

// 타입/인터페이스: PascalCase
type UserRole = 'admin' | 'user' | 'guest';
interface PostData {
  id: string;
  title: string;
}

// Props 타입: 컴포넌트명 + Props
interface UserProfileProps {
  user: User;
  showAvatar?: boolean;
}
interface PostCardProps {
  post: Post;
  onDelete?: (id: string) => void;
}

// Server Actions: camelCase, 동사로 시작
export async function createPost(formData: FormData) {}
export async function updateUserProfile(formData: FormData) {}
export async function deleteComment(commentId: string) {}

// 이벤트 핸들러: handle + 이벤트명
function handleSubmit(e: FormEvent) {}
function handleClick() {}
function handleInputChange(value: string) {}

// 제네릭 타입 파라미터: 의미 있는 이름 또는 T
type ApiResponse<TData> = { data: TData; error: null } | { data: null; error: string };
type PaginatedList<TItem> = { items: TItem[]; total: number; page: number };
```

### App Router 디렉토리 구조 상세

#### Route Groups

```
app/
├── (auth)/                        # URL에 영향 없음, 레이아웃 그룹화용
│   ├── login/page.tsx             # /login
│   ├── register/page.tsx          # /register
│   ├── forgot-password/page.tsx   # /forgot-password
│   └── layout.tsx                 # 인증 페이지 전용 레이아웃 (로고만 있는 미니멀)
├── (dashboard)/                   # URL에 영향 없음
│   ├── dashboard/page.tsx         # /dashboard
│   ├── dashboard/analytics/page.tsx # /dashboard/analytics
│   ├── settings/
│   │   ├── page.tsx               # /settings
│   │   ├── profile/page.tsx       # /settings/profile
│   │   └── billing/page.tsx       # /settings/billing
│   └── layout.tsx                 # 대시보드 레이아웃 (사이드바 + 헤더)
├── (marketing)/                   # URL에 영향 없음
│   ├── page.tsx                   # / (홈)
│   ├── about/page.tsx             # /about
│   ├── pricing/page.tsx           # /pricing
│   └── layout.tsx                 # 마케팅 레이아웃 (네비게이션 + 푸터)
```

#### 병렬 라우트 (Parallel Routes)

```
app/
├── (dashboard)/
│   ├── dashboard/
│   │   ├── page.tsx
│   │   ├── @analytics/           # 슬롯: 분석 패널
│   │   │   ├── page.tsx
│   │   │   └── loading.tsx
│   │   ├── @notifications/       # 슬롯: 알림 패널
│   │   │   ├── page.tsx
│   │   │   └── default.tsx       # 매칭 안 될 때 기본 렌더링
│   │   └── layout.tsx            # 슬롯을 받는 레이아웃
```

```typescript
// app/(dashboard)/dashboard/layout.tsx
export default function DashboardLayout({
  children,
  analytics,
  notifications,
}: {
  children: React.ReactNode;
  analytics: React.ReactNode;
  notifications: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-12 gap-4">
      <main className="col-span-8">{children}</main>
      <aside className="col-span-4 space-y-4">
        {analytics}
        {notifications}
      </aside>
    </div>
  );
}
```

#### 인터셉팅 라우트 (Intercepting Routes)

```
app/
├── posts/
│   ├── page.tsx                   # 게시글 목록
│   ├── [id]/
│   │   └── page.tsx               # 게시글 상세 (직접 접근)
│   └── (.)[id]/                   # 같은 레벨 인터셉트
│       └── page.tsx               # 모달로 게시글 상세 표시
├── @modal/                        # 병렬 라우트와 조합
│   ├── (..)posts/[id]/
│   │   └── page.tsx
│   └── default.tsx
```

인터셉팅 라우트 규칙:

- `(.)` : 같은 레벨
- `(..)` : 한 레벨 위
- `(..)(..)` : 두 레벨 위
- `(...)` : 루트(`app/`)부터

### 파일 컨벤션

#### page.tsx - 라우트 페이지

```typescript
// app/posts/page.tsx
import { Suspense } from 'react';
import { PostList } from '@/components/features/posts/post-list';
import { PostListSkeleton } from '@/components/features/posts/post-list-skeleton';

// 정적 메타데이터
export const metadata = {
  title: '게시글 목록',
  description: '모든 게시글을 확인하세요.',
};

// 동적 메타데이터 (동적 페이지용)
// export async function generateMetadata({ params }: Props): Promise<Metadata> {
//   const post = await getPost(params.id);
//   return { title: post.title };
// }

export default async function PostsPage({
  searchParams,
}: {
  searchParams: { page?: string; q?: string };
}) {
  const page = Number(searchParams.page) || 1;
  const query = searchParams.q || '';

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold mb-6">게시글</h1>
      <Suspense fallback={<PostListSkeleton />}>
        <PostList page={page} query={query} />
      </Suspense>
    </div>
  );
}
```

#### layout.tsx - 레이아웃

```typescript
// app/layout.tsx
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: {
    default: '내 앱',
    template: '%s | 내 앱',     // 하위 페이지: "게시글 | 내 앱"
  },
  description: '앱 설명',
  metadataBase: new URL('https://example.com'),
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko" className={inter.variable}>
      <body className="font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
```

#### loading.tsx - 로딩 UI

```typescript
// app/(dashboard)/dashboard/loading.tsx
import { Skeleton } from '@/components/ui/skeleton';

export default function DashboardLoading() {
  return (
    <div className="space-y-4 p-6">
      <Skeleton className="h-8 w-64" />
      <div className="grid grid-cols-3 gap-4">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
      <Skeleton className="h-64" />
    </div>
  );
}
```

#### error.tsx - 에러 바운더리

```typescript
// app/(dashboard)/dashboard/error.tsx
'use client'; // 필수: error.tsx는 반드시 Client Component

import { useEffect } from 'react';

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // 에러 리포팅 서비스에 전송
    console.error('Dashboard error:', error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
      <h2 className="text-xl font-semibold">문제가 발생했습니다</h2>
      <p className="text-muted-foreground">{error.message}</p>
      <button
        onClick={reset}
        className="px-4 py-2 bg-primary text-white rounded-md"
      >
        다시 시도
      </button>
    </div>
  );
}
```

#### global-error.tsx - 루트 에러 바운더리

```typescript
// app/global-error.tsx
'use client';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html>
      <body>
        <div className="flex flex-col items-center justify-center min-h-screen">
          <h2>심각한 오류가 발생했습니다</h2>
          <button onClick={reset}>다시 시도</button>
        </div>
      </body>
    </html>
  );
}
```

#### not-found.tsx - 404 페이지

```typescript
// app/not-found.tsx
import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
      <h2 className="text-4xl font-bold">404</h2>
      <p className="text-lg text-muted-foreground">
        페이지를 찾을 수 없습니다.
      </p>
      <Link
        href="/"
        className="px-4 py-2 bg-primary text-white rounded-md"
      >
        홈으로 돌아가기
      </Link>
    </div>
  );
}
```

#### route.ts - Route Handler

```typescript
// app/api/posts/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { z } from 'zod';

const createPostSchema = z.object({
  title: z.string().min(1).max(200),
  content: z.string().min(1),
});

// GET /api/posts
export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const page = Number(searchParams.get('page')) || 1;

  const posts = await db.post.findMany({
    take: 20,
    skip: (page - 1) * 20,
  });

  return NextResponse.json({ posts });
}

// POST /api/posts
export async function POST(request: NextRequest) {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const body = await request.json();
  const parsed = createPostSchema.safeParse(body);

  if (!parsed.success) {
    return NextResponse.json(
      { error: parsed.error.flatten() },
      { status: 400 }
    );
  }

  const post = await db.post.create({
    data: { ...parsed.data, authorId: session.user.id },
  });

  return NextResponse.json({ post }, { status: 201 });
}
```

### import 순서 규칙

```typescript
// 1. React / Next.js 내장 모듈
import { Suspense, cache } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { redirect, notFound } from 'next/navigation';

// 2. 외부 라이브러리 (node_modules)
import { z } from 'zod';
import { format } from 'date-fns';
import { clsx } from 'clsx';

// 3. 내부 모듈 (@/ alias)
import { auth } from '@/lib/auth';
import { db } from '@/lib/db';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { PostCard } from '@/components/features/posts/post-card';
import { createPost } from '@/actions/post-actions';

// 4. 타입 import (type 키워드 사용)
import type { Metadata } from 'next';
import type { Post, User } from '@/types';

// 5. 스타일 (CSS Modules 사용 시)
import styles from './page.module.css';
```

### Server Component vs Client Component 코드 구조

```typescript
// ===== Server Component (기본) =====
// 파일 상단에 아무 지시어 없음
// async 가능, hooks 불가, 브라우저 API 불가
import { db } from '@/lib/db';

export default async function PostPage({ params }: { params: { id: string } }) {
  // 직접 DB 쿼리 가능
  const post = await db.post.findUnique({ where: { id: params.id } });
  if (!post) notFound();

  return (
    <article>
      <h1>{post.title}</h1>
      <p>{post.content}</p>
      {/* Client Component를 자식으로 사용 */}
      <LikeButton postId={post.id} initialLikes={post.likes} />
    </article>
  );
}

// ===== Client Component =====
// 파일 최상단에 'use client' 선언 필수
'use client';

import { useState, useTransition } from 'react';
import { likePost } from '@/actions/post-actions';

export function LikeButton({ postId, initialLikes }: {
  postId: string;
  initialLikes: number;
}) {
  const [likes, setLikes] = useState(initialLikes);
  const [isPending, startTransition] = useTransition();

  function handleLike() {
    startTransition(async () => {
      const result = await likePost(postId);
      if (result.success) setLikes(result.likes);
    });
  }

  return (
    <button onClick={handleLike} disabled={isPending}>
      {isPending ? '처리 중...' : `좋아요 ${likes}`}
    </button>
  );
}
```

### TypeScript 활용 패턴

#### Props 타입 정의

```typescript
// 기본 Props
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
}

// HTML 속성 확장
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
}

// children을 포함하는 레이아웃 Props
interface LayoutProps {
  children: React.ReactNode;
  params: { locale: string };
}

// 제네릭 컴포넌트
interface DataTableProps<TData> {
  data: TData[];
  columns: ColumnDef<TData>[];
  onRowClick?: (row: TData) => void;
}

export function DataTable<TData>({ data, columns, onRowClick }: DataTableProps<TData>) {
  // ...
}
```

#### Server Action 타입

```typescript
// 공통 Action 응답 타입
type ActionState<TData = void> =
  | { success: true; data: TData; error: null }
  | { success: false; data: null; error: string };

// 폼 에러 포함 Action 응답
type FormActionState<TData = void> =
  | { success: true; data: TData; errors: null }
  | { success: false; data: null; errors: Record<string, string[]> };
```

### CSS / 스타일링 패턴

#### cn 유틸리티 함수 (clsx + tailwind-merge)

```typescript
// lib/utils.ts
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

#### 컴포넌트 스타일링 패턴

```typescript
// 조건부 클래스 적용
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
}

export function Button({ variant = 'primary', size = 'md', className, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        // 기본 스타일
        'inline-flex items-center justify-center rounded-md font-medium transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
        'disabled:pointer-events-none disabled:opacity-50',
        // variant별 스타일
        {
          'bg-primary text-white hover:bg-primary/90': variant === 'primary',
          'bg-secondary text-secondary-foreground hover:bg-secondary/80': variant === 'secondary',
          'hover:bg-accent hover:text-accent-foreground': variant === 'ghost',
        },
        // size별 스타일
        {
          'h-8 px-3 text-sm': size === 'sm',
          'h-10 px-4 text-sm': size === 'md',
          'h-12 px-6 text-base': size === 'lg',
        },
        // 외부에서 전달된 클래스 (오버라이드 가능)
        className
      )}
      {...props}
    />
  );
}
```

### Metadata API 활용

```typescript
// 정적 메타데이터
export const metadata: Metadata = {
  title: '게시글 목록',
  description: '모든 게시글을 확인하세요.',
  openGraph: {
    title: '게시글 목록',
    description: '모든 게시글을 확인하세요.',
    type: 'website',
  },
};

// 동적 메타데이터
export async function generateMetadata(
  { params }: { params: { id: string } },
  parent: ResolvingMetadata
): Promise<Metadata> {
  const post = await getPost(params.id);
  const previousImages = (await parent).openGraph?.images || [];

  return {
    title: post.title,
    description: post.excerpt,
    openGraph: {
      title: post.title,
      description: post.excerpt,
      images: [post.ogImage, ...previousImages],
    },
  };
}
```

---

## 3. 보안 필수사항

### XSS 방지 상세

#### dangerouslySetInnerHTML 대체

```typescript
// [금지] 절대 사용하지 않는다
function Dangerous({ html }: { html: string }) {
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}

// [허용] 불가피하게 HTML 렌더링이 필요한 경우 DOMPurify 사용
'use client';
import DOMPurify from 'dompurify';

function SafeHtml({ html }: { html: string }) {
  const sanitized = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li', 'h1', 'h2', 'h3'],
    ALLOWED_ATTR: ['href', 'target', 'rel'],
    ALLOW_DATA_ATTR: false,
  });

  return <div dangerouslySetInnerHTML={{ __html: sanitized }} />;
}

// [권장] 마크다운 렌더링이 필요한 경우 서버에서 변환
// Server Component에서 처리하면 클라이언트 번들에 DOMPurify 불필요
import { remark } from 'remark';
import remarkHtml from 'remark-html';
import remarkGfm from 'remark-gfm';
import sanitizeHtml from 'sanitize-html';

async function MarkdownRenderer({ content }: { content: string }) {
  const result = await remark().use(remarkGfm).use(remarkHtml).process(content);
  const clean = sanitizeHtml(result.toString(), {
    allowedTags: sanitizeHtml.defaults.allowedTags.concat(['img']),
    allowedAttributes: {
      ...sanitizeHtml.defaults.allowedAttributes,
      img: ['src', 'alt', 'width', 'height'],
    },
  });

  return <div dangerouslySetInnerHTML={{ __html: clean }} />;
}
```

#### URL 검증

```typescript
// 안전한 URL 검증 함수
function isValidUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return ['http:', 'https:'].includes(parsed.protocol);
  } catch {
    return false;
  }
}

// href에 사용자 입력 사용 시
function SafeLink({ href, children }: { href: string; children: React.ReactNode }) {
  // javascript: 프로토콜 차단
  if (!isValidUrl(href)) {
    return <span>{children}</span>;
  }
  return (
    <a href={href} rel="noopener noreferrer" target="_blank">
      {children}
    </a>
  );
}

// [금지] 사용자 입력을 직접 href/src에 삽입
// <a href={userInput}>     // XSS 위험: javascript:alert(1)
// <img src={userInput} />  // 위험
// <iframe src={userInput}> // 위험
```

#### 보안 헤더 설정 (next.config.js)

```javascript
// next.config.js
const nextConfig = {
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=31536000; includeSubDomains',
          },
        ],
      },
    ];
  },
};
```

#### Content Security Policy

```javascript
// next.config.js
const cspHeader = `
  default-src 'self';
  script-src 'self' 'nonce-{NONCE}' 'strict-dynamic';
  style-src 'self' 'unsafe-inline';
  img-src 'self' blob: data: https:;
  font-src 'self';
  object-src 'none';
  base-uri 'self';
  form-action 'self';
  frame-ancestors 'none';
  upgrade-insecure-requests;
`.replace(/\n/g, '');

// middleware.ts에서 nonce 주입
import { NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString('base64');
  const csp = cspHeader.replace('{NONCE}', nonce);

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-nonce', nonce);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set('Content-Security-Policy', csp);

  return response;
}
```

### Server Actions 보안 상세

#### 인증 확인 패턴

```typescript
// actions/post-actions.ts
'use server';

import { auth } from '@/lib/auth';
import { db } from '@/lib/db';
import { z } from 'zod';
import { revalidatePath } from 'next/cache';

// 인증 확인 헬퍼
async function getAuthenticatedUser() {
  const session = await auth();
  if (!session?.user?.id) {
    throw new Error('Unauthorized');
  }
  return session.user;
}

// 권한 확인 헬퍼
async function checkPermission(resourceId: string, userId: string) {
  const resource = await db.post.findUnique({
    where: { id: resourceId },
    select: { authorId: true },
  });

  if (!resource || resource.authorId !== userId) {
    throw new Error('Forbidden');
  }
}

const createPostSchema = z.object({
  title: z.string().min(1, '제목을 입력하세요').max(200, '제목은 200자 이하'),
  content: z.string().min(1, '내용을 입력하세요'),
  categoryId: z.string().uuid('유효하지 않은 카테고리'),
  published: z.boolean().default(false),
});

export async function createPost(
  prevState: FormActionState,
  formData: FormData
): Promise<FormActionState> {
  // 1. 인증 확인
  const user = await getAuthenticatedUser();

  // 2. 입력 검증
  const rawData = {
    title: formData.get('title'),
    content: formData.get('content'),
    categoryId: formData.get('categoryId'),
    published: formData.get('published') === 'true',
  };

  const parsed = createPostSchema.safeParse(rawData);
  if (!parsed.success) {
    return {
      success: false,
      data: null,
      errors: parsed.error.flatten().fieldErrors as Record<string, string[]>,
    };
  }

  // 3. DB 작업
  try {
    const post = await db.post.create({
      data: {
        ...parsed.data,
        authorId: user.id,
      },
    });

    revalidatePath('/posts');

    return { success: true, data: post, errors: null };
  } catch (error) {
    return {
      success: false,
      data: null,
      errors: { _form: ['게시글 생성에 실패했습니다.'] },
    };
  }
}

export async function deletePost(postId: string): Promise<ActionState> {
  const user = await getAuthenticatedUser();
  await checkPermission(postId, user.id);

  try {
    await db.post.delete({ where: { id: postId } });
    revalidatePath('/posts');
    return { success: true, data: undefined, error: null };
  } catch {
    return { success: false, data: null, error: '삭제에 실패했습니다.' };
  }
}
```

#### Zod 입력 검증 상세 패턴

```typescript
// lib/validations.ts
import { z } from 'zod';

// 기본 스키마
export const emailSchema = z.string().email('유효한 이메일을 입력하세요');
export const passwordSchema = z.string()
  .min(8, '비밀번호는 8자 이상')
  .max(100, '비밀번호는 100자 이하')
  .regex(/[A-Z]/, '대문자를 포함해야 합니다')
  .regex(/[0-9]/, '숫자를 포함해야 합니다')
  .regex(/[^A-Za-z0-9]/, '특수문자를 포함해야 합니다');

// coerce: FormData의 문자열을 숫자/날짜로 자동 변환
export const paginationSchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20),
});

// transform: 입력값 변환
export const createUserSchema = z.object({
  email: z.string().email().transform((v) => v.toLowerCase().trim()),
  name: z.string().min(1).max(50).transform((v) => v.trim()),
});

// refine: 커스텀 검증
export const registerSchema = z.object({
  email: emailSchema,
  password: passwordSchema,
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: '비밀번호가 일치하지 않습니다',
  path: ['confirmPassword'],
});

// discriminatedUnion: 태그 기반 유니온
export const notificationSchema = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('email'),
    email: z.string().email(),
    subject: z.string().min(1),
  }),
  z.object({
    type: z.literal('sms'),
    phoneNumber: z.string().regex(/^010-\d{4}-\d{4}$/),
  }),
  z.object({
    type: z.literal('push'),
    deviceToken: z.string().min(1),
  }),
]);

// 파일 업로드 검증
export const fileUploadSchema = z.object({
  file: z
    .instanceof(File)
    .refine((f) => f.size <= 5 * 1024 * 1024, '파일 크기는 5MB 이하')
    .refine(
      (f) => ['image/jpeg', 'image/png', 'image/webp'].includes(f.type),
      'JPG, PNG, WebP 파일만 허용'
    ),
});
```

#### Rate Limiting 구현

```typescript
// lib/rate-limit.ts
const rateLimit = new Map<string, { count: number; resetTime: number }>();

export function checkRateLimit(
  key: string,
  limit: number = 10,
  windowMs: number = 60_000
): boolean {
  const now = Date.now();
  const record = rateLimit.get(key);

  if (!record || now > record.resetTime) {
    rateLimit.set(key, { count: 1, resetTime: now + windowMs });
    return true;
  }

  if (record.count >= limit) {
    return false;
  }

  record.count++;
  return true;
}

// Server Action에서 사용
'use server';
import { headers } from 'next/headers';
import { checkRateLimit } from '@/lib/rate-limit';

export async function submitForm(formData: FormData) {
  const ip = headers().get('x-forwarded-for') || 'unknown';

  if (!checkRateLimit(`submit:${ip}`, 5, 60_000)) {
    return { error: '요청이 너무 많습니다. 잠시 후 다시 시도하세요.' };
  }

  // 나머지 로직...
}
```

### 인증/인가 상세

#### NextAuth.js (Auth.js) v5 설정

```typescript
// lib/auth.ts
import NextAuth from 'next-auth';
import { PrismaAdapter } from '@auth/prisma-adapter';
import GitHub from 'next-auth/providers/github';
import Google from 'next-auth/providers/google';
import Credentials from 'next-auth/providers/credentials';
import { db } from '@/lib/db';
import { loginSchema } from '@/lib/validations';
import bcrypt from 'bcryptjs';

export const { handlers, auth, signIn, signOut } = NextAuth({
  adapter: PrismaAdapter(db),
  session: { strategy: 'jwt' },
  pages: {
    signIn: '/login',
    error: '/login',
  },
  providers: [
    GitHub({
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
    }),
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
    Credentials({
      async authorize(credentials) {
        const parsed = loginSchema.safeParse(credentials);
        if (!parsed.success) return null;

        const user = await db.user.findUnique({
          where: { email: parsed.data.email },
        });
        if (!user?.hashedPassword) return null;

        const isValid = await bcrypt.compare(
          parsed.data.password,
          user.hashedPassword
        );
        if (!isValid) return null;

        return { id: user.id, email: user.email, name: user.name, role: user.role };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.role = (user as any).role;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string;
        session.user.role = token.role as string;
      }
      return session;
    },
    async authorized({ auth, request }) {
      const isLoggedIn = !!auth?.user;
      const isOnDashboard = request.nextUrl.pathname.startsWith('/dashboard');
      if (isOnDashboard && !isLoggedIn) return false;
      return true;
    },
  },
});
```

#### middleware.ts 전체 구현

```typescript
// middleware.ts
import { auth } from '@/lib/auth';
import { NextResponse } from 'next/server';

// 공개 경로 (인증 불필요)
const publicPaths = ['/', '/login', '/register', '/about', '/pricing'];
// 인증된 사용자가 접근 불가한 경로 (로그인 페이지 등)
const authPaths = ['/login', '/register'];
// 관리자 전용 경로
const adminPaths = ['/admin'];

export default auth((req) => {
  const { pathname } = req.nextUrl;
  const isLoggedIn = !!req.auth?.user;
  const userRole = req.auth?.user?.role;

  // 공개 경로: 통과
  if (publicPaths.some((p) => pathname === p)) {
    // 로그인된 사용자가 auth 경로 접근 시 대시보드로 리다이렉트
    if (isLoggedIn && authPaths.some((p) => pathname.startsWith(p))) {
      return NextResponse.redirect(new URL('/dashboard', req.url));
    }
    return NextResponse.next();
  }

  // 비로그인 사용자: 로그인 페이지로
  if (!isLoggedIn) {
    const loginUrl = new URL('/login', req.url);
    loginUrl.searchParams.set('callbackUrl', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // 관리자 경로 접근 제어
  if (adminPaths.some((p) => pathname.startsWith(p)) && userRole !== 'admin') {
    return NextResponse.redirect(new URL('/dashboard', req.url));
  }

  return NextResponse.next();
});

export const config = {
  matcher: [
    // 정적 파일과 API 라우트 제외
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};
```

#### 서버 컴포넌트에서 인증 확인

```typescript
// app/(dashboard)/dashboard/page.tsx
import { auth } from '@/lib/auth';
import { redirect } from 'next/navigation';

export default async function DashboardPage() {
  const session = await auth();

  // 미들웨어에서 이미 확인하지만, 추가 보안 레이어
  if (!session?.user) {
    redirect('/login');
  }

  // 역할 기반 접근 제어
  if (session.user.role !== 'admin') {
    redirect('/dashboard');
  }

  return (
    <div>
      <h1>환영합니다, {session.user.name}</h1>
    </div>
  );
}
```

### 시크릿 관리

```
# .env.local (gitignore 필수)

# 서버 전용 (NEXT_PUBLIC_ 접두사 없음)
DATABASE_URL="postgresql://user:pass@localhost:5432/db"
AUTH_SECRET="your-secret-key"
GITHUB_CLIENT_SECRET="ghp_xxxx"
STRIPE_SECRET_KEY="sk_live_xxxx"

# 클라이언트 노출 허용 (NEXT_PUBLIC_ 접두사)
NEXT_PUBLIC_APP_URL="https://example.com"
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY="pk_live_xxxx"
```

```typescript
// 서버 전용 모듈 보호
// lib/db.ts
import 'server-only'; // 클라이언트에서 import 시 빌드 에러

import { PrismaClient } from '@prisma/client';

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient };

export const db = globalForPrisma.prisma || new PrismaClient();

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = db;
```

---

## 4. 생산성 가이드

### App Router 구조 상세

#### Route Handlers (API Routes)

```typescript
// app/api/upload/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth';

export async function POST(request: NextRequest) {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const formData = await request.formData();
  const file = formData.get('file') as File;

  if (!file) {
    return NextResponse.json({ error: 'No file provided' }, { status: 400 });
  }

  // 파일 크기 및 타입 검증
  if (file.size > 5 * 1024 * 1024) {
    return NextResponse.json({ error: 'File too large' }, { status: 400 });
  }

  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
  if (!allowedTypes.includes(file.type)) {
    return NextResponse.json({ error: 'Invalid file type' }, { status: 400 });
  }

  // 업로드 로직...
  const bytes = await file.arrayBuffer();
  const buffer = Buffer.from(bytes);

  return NextResponse.json({ url: '/uploads/image.jpg' }, { status: 201 });
}

// Webhook 처리 (외부 서비스 → 우리 서버)
// app/api/webhooks/stripe/route.ts
import { headers } from 'next/headers';
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export async function POST(request: NextRequest) {
  const body = await request.text();
  const signature = headers().get('stripe-signature')!;

  try {
    const event = stripe.webhooks.constructEvent(
      body,
      signature,
      process.env.STRIPE_WEBHOOK_SECRET!
    );

    switch (event.type) {
      case 'checkout.session.completed':
        // 결제 완료 처리
        break;
    }

    return NextResponse.json({ received: true });
  } catch (err) {
    return NextResponse.json({ error: 'Invalid signature' }, { status: 400 });
  }
}
```

### Server/Client Components 분리 상세

#### "use client" 경계 설계 원칙

```
규칙: "use client" 경계를 가능한 한 트리의 하단(leaf)에 배치

[Server] page.tsx
├── [Server] ArticleContent (정적 텍스트, DB 데이터)
├── [Server] AuthorInfo (서버에서 가져온 유저 정보)
├── [Client] LikeButton (상호작용)       ← 경계: 최소 단위
├── [Client] CommentForm (폼 입력)      ← 경계: 최소 단위
└── [Server] RelatedPosts (DB 쿼리)
```

#### Composition 패턴 (Server + Client 조합)

```typescript
// Server Component에서 Client Component를 children으로 감싸기
// app/layout.tsx (Server Component)
import { auth } from '@/lib/auth';
import { Sidebar } from '@/components/layout/sidebar'; // Client Component

export default async function Layout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  const user = session?.user;

  return (
    <div className="flex">
      {/* Client Component에 서버 데이터를 props로 전달 */}
      <Sidebar user={user} />
      <main className="flex-1">
        {/* children은 Server Component 가능 */}
        {children}
      </main>
    </div>
  );
}

// Server Component를 Client Component의 children으로 전달
// components/features/modal-wrapper.tsx
'use client';
import { useState } from 'react';

export function ModalWrapper({ trigger, children }: {
  trigger: React.ReactNode;
  children: React.ReactNode; // Server Component 가능
}) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button onClick={() => setOpen(true)}>{trigger}</button>
      {open && (
        <div className="modal">
          {children}  {/* 서버에서 렌더링된 내용 */}
          <button onClick={() => setOpen(false)}>닫기</button>
        </div>
      )}
    </>
  );
}

// 사용 (page.tsx - Server Component)
export default async function Page() {
  const data = await fetchData(); // 서버에서 데이터 가져오기

  return (
    <ModalWrapper trigger="상세 보기">
      {/* 이 부분은 Server Component로 렌더링됨 */}
      <DetailContent data={data} />
    </ModalWrapper>
  );
}
```

### 데이터 페칭 전략 상세

#### Server Component에서의 fetch

```typescript
// 기본 fetch (기본 캐싱 적용)
async function getPosts() {
  const res = await fetch('https://api.example.com/posts');
  if (!res.ok) throw new Error('Failed to fetch posts');
  return res.json();
}

// 시간 기반 재검증 (ISR)
async function getProducts() {
  const res = await fetch('https://api.example.com/products', {
    next: { revalidate: 3600 }, // 1시간마다 재검증
  });
  return res.json();
}

// 캐시 없음 (항상 최신 데이터)
async function getNotifications() {
  const res = await fetch('https://api.example.com/notifications', {
    cache: 'no-store',
  });
  return res.json();
}

// 태그 기반 재검증
async function getPost(id: string) {
  const res = await fetch(`https://api.example.com/posts/${id}`, {
    next: { tags: [`post-${id}`] },
  });
  return res.json();
}

// Server Action에서 태그 무효화
'use server';
import { revalidateTag } from 'next/cache';

export async function updatePost(id: string, formData: FormData) {
  await db.post.update({ where: { id }, data: { /* ... */ } });
  revalidateTag(`post-${id}`);
}
```

#### 병렬 데이터 페칭

```typescript
// [권장] 병렬 fetch - 독립적인 데이터를 동시에 가져오기
export default async function DashboardPage() {
  // Promise.all로 병렬 실행
  const [user, posts, notifications] = await Promise.all([
    getUser(),
    getPosts(),
    getNotifications(),
  ]);

  return (
    <div>
      <UserProfile user={user} />
      <PostList posts={posts} />
      <NotificationList notifications={notifications} />
    </div>
  );
}

// [주의] 순차적 fetch (워터폴) - 피해야 할 패턴
// 아래처럼 하면 각 요청이 순차적으로 실행됨
export default async function BadPage() {
  const user = await getUser();           // 200ms
  const posts = await getPosts();         // 300ms (user 완료 후)
  const notifications = await getNotifications(); // 100ms (posts 완료 후)
  // 총 600ms (병렬이면 300ms)
}

// [대안] Suspense로 독립적 스트리밍
export default function DashboardPage() {
  return (
    <div>
      <Suspense fallback={<UserSkeleton />}>
        <UserSection />  {/* 각각 독립적으로 스트리밍 */}
      </Suspense>
      <Suspense fallback={<PostSkeleton />}>
        <PostSection />
      </Suspense>
    </div>
  );
}
```

#### Server Actions + useFormState + useFormStatus

```typescript
// actions/post-actions.ts
'use server';
import { z } from 'zod';
import { auth } from '@/lib/auth';
import { revalidatePath } from 'next/cache';

const schema = z.object({
  title: z.string().min(1, '제목 필수').max(200),
  content: z.string().min(1, '내용 필수'),
});

type State = {
  errors?: { title?: string[]; content?: string[]; _form?: string[] };
  success?: boolean;
};

export async function createPost(prevState: State, formData: FormData): Promise<State> {
  const session = await auth();
  if (!session) return { errors: { _form: ['로그인이 필요합니다'] } };

  const parsed = schema.safeParse({
    title: formData.get('title'),
    content: formData.get('content'),
  });

  if (!parsed.success) {
    return { errors: parsed.error.flatten().fieldErrors };
  }

  try {
    await db.post.create({
      data: { ...parsed.data, authorId: session.user.id },
    });
    revalidatePath('/posts');
    return { success: true };
  } catch {
    return { errors: { _form: ['생성 실패'] } };
  }
}

// components/features/posts/create-post-form.tsx
'use client';
import { useFormState, useFormStatus } from 'react-dom';
import { createPost } from '@/actions/post-actions';

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending}>
      {pending ? '저장 중...' : '게시글 작성'}
    </button>
  );
}

export function CreatePostForm() {
  const [state, formAction] = useFormState(createPost, {});

  return (
    <form action={formAction} className="space-y-4">
      <div>
        <label htmlFor="title">제목</label>
        <input id="title" name="title" type="text" />
        {state.errors?.title && (
          <p className="text-red-500 text-sm">{state.errors.title[0]}</p>
        )}
      </div>

      <div>
        <label htmlFor="content">내용</label>
        <textarea id="content" name="content" rows={5} />
        {state.errors?.content && (
          <p className="text-red-500 text-sm">{state.errors.content[0]}</p>
        )}
      </div>

      {state.errors?._form && (
        <p className="text-red-500">{state.errors._form[0]}</p>
      )}

      {state.success && (
        <p className="text-green-500">게시글이 작성되었습니다!</p>
      )}

      <SubmitButton />
    </form>
  );
}
```

### 상태 관리

#### URL 상태 (searchParams)

```typescript
// Server Component에서 searchParams 읽기
export default async function ProductsPage({
  searchParams,
}: {
  searchParams: { category?: string; sort?: string; page?: string };
}) {
  const category = searchParams.category || 'all';
  const sort = searchParams.sort || 'newest';
  const page = Number(searchParams.page) || 1;

  const products = await getProducts({ category, sort, page });
  return <ProductList products={products} />;
}

// Client Component에서 searchParams 조작
'use client';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import { useCallback } from 'react';

export function Filters() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const createQueryString = useCallback(
    (name: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set(name, value);
      return params.toString();
    },
    [searchParams]
  );

  function handleCategoryChange(category: string) {
    router.push(`${pathname}?${createQueryString('category', category)}`);
  }

  return (
    <select
      value={searchParams.get('category') || 'all'}
      onChange={(e) => handleCategoryChange(e.target.value)}
    >
      <option value="all">전체</option>
      <option value="electronics">전자기기</option>
      <option value="clothing">의류</option>
    </select>
  );
}
```

#### useOptimistic 패턴

```typescript
'use client';
import { useOptimistic, useTransition } from 'react';
import { toggleLike } from '@/actions/post-actions';

export function LikeButton({ postId, isLiked, likeCount }: {
  postId: string;
  isLiked: boolean;
  likeCount: number;
}) {
  const [isPending, startTransition] = useTransition();
  const [optimistic, setOptimistic] = useOptimistic(
    { isLiked, likeCount },
    (state, newIsLiked: boolean) => ({
      isLiked: newIsLiked,
      likeCount: newIsLiked ? state.likeCount + 1 : state.likeCount - 1,
    })
  );

  function handleClick() {
    startTransition(async () => {
      setOptimistic(!optimistic.isLiked);
      await toggleLike(postId);
    });
  }

  return (
    <button onClick={handleClick} disabled={isPending}>
      {optimistic.isLiked ? '❤️' : '🤍'} {optimistic.likeCount}
    </button>
  );
}
```

### 테스트 전략 상세

#### Jest + React Testing Library 설정

```typescript
// jest.config.ts
import type { Config } from 'jest';
import nextJest from 'next/jest';

const createJestConfig = nextJest({ dir: './' });

const config: Config = {
  setupFilesAfterSetup: ['<rootDir>/jest.setup.ts'],
  testEnvironment: 'jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  testPathIgnorePatterns: ['<rootDir>/e2e/'],
};

export default createJestConfig(config);

// jest.setup.ts
import '@testing-library/jest-dom';
```

#### 컴포넌트 테스트

```typescript
// __tests__/components/post-card.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PostCard } from '@/components/features/posts/post-card';

const mockPost = {
  id: '1',
  title: '테스트 게시글',
  content: '테스트 내용',
  createdAt: new Date('2024-01-01'),
  author: { name: '홍길동' },
};

describe('PostCard', () => {
  it('게시글 제목을 표시한다', () => {
    render(<PostCard post={mockPost} />);
    expect(screen.getByText('테스트 게시글')).toBeInTheDocument();
  });

  it('삭제 버튼 클릭 시 onDelete 호출', async () => {
    const user = userEvent.setup();
    const onDelete = jest.fn();

    render(<PostCard post={mockPost} onDelete={onDelete} />);
    await user.click(screen.getByRole('button', { name: '삭제' }));

    expect(onDelete).toHaveBeenCalledWith('1');
  });
});
```

#### Server Action 테스트

```typescript
// __tests__/actions/post-actions.test.ts
import { createPost } from '@/actions/post-actions';

// auth 모킹
jest.mock('@/lib/auth', () => ({
  auth: jest.fn(),
}));

// db 모킹
jest.mock('@/lib/db', () => ({
  db: {
    post: {
      create: jest.fn(),
    },
  },
}));

import { auth } from '@/lib/auth';
import { db } from '@/lib/db';

describe('createPost', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('미인증 시 에러 반환', async () => {
    (auth as jest.Mock).mockResolvedValue(null);

    const formData = new FormData();
    formData.set('title', '테스트');
    formData.set('content', '내용');

    const result = await createPost({}, formData);
    expect(result.errors?._form).toBeDefined();
  });

  it('유효한 입력 시 게시글 생성', async () => {
    (auth as jest.Mock).mockResolvedValue({
      user: { id: 'user-1' },
    });
    (db.post.create as jest.Mock).mockResolvedValue({ id: 'post-1' });

    const formData = new FormData();
    formData.set('title', '새 게시글');
    formData.set('content', '게시글 내용');

    const result = await createPost({}, formData);
    expect(result.success).toBe(true);
  });
});
```

#### Playwright E2E 테스트

```typescript
// e2e/posts.spec.ts
import { test, expect } from '@playwright/test';

test.describe('게시글 기능', () => {
  test.beforeEach(async ({ page }) => {
    // 로그인
    await page.goto('/login');
    await page.fill('[name="email"]', 'test@example.com');
    await page.fill('[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/dashboard');
  });

  test('게시글 작성', async ({ page }) => {
    await page.goto('/posts/new');
    await page.fill('[name="title"]', '테스트 게시글');
    await page.fill('[name="content"]', '테스트 내용');
    await page.click('button[type="submit"]');

    await expect(page.getByText('게시글이 작성되었습니다')).toBeVisible();
  });

  test('게시글 목록 표시', async ({ page }) => {
    await page.goto('/posts');
    await expect(page.getByRole('heading', { name: '게시글' })).toBeVisible();
    const items = page.locator('[data-testid="post-card"]');
    await expect(items).toHaveCount(10); // 기본 페이지 크기
  });
});

// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  webServer: {
    command: 'npm run dev',
    port: 3000,
    reuseExistingServer: !process.env.CI,
  },
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 5'] } },
  ],
});
```

### CLI 명령어 전체 리스트

```bash
# 개발
npm run dev                      # 개발 서버 시작 (Turbopack)
npm run dev -- --port 4000       # 포트 지정
npm run dev -- --turbo           # Turbopack 명시

# 빌드 & 배포
npm run build                    # 프로덕션 빌드
npm run start                    # 프로덕션 서버 시작
npm run lint                     # ESLint 실행
npm run lint -- --fix            # ESLint 자동 수정

# 테스트
npm run test                     # Jest 실행
npm run test -- --watch          # 감시 모드
npm run test -- --coverage       # 커버리지 리포트
npx playwright test              # E2E 테스트
npx playwright test --ui         # E2E 테스트 UI 모드

# 분석 & 디버깅
npx next info                    # 환경 정보 출력
ANALYZE=true npm run build       # 번들 분석

# DB (Prisma 사용 시)
npx prisma generate              # Prisma Client 생성
npx prisma db push               # 스키마 → DB 반영
npx prisma migrate dev           # 마이그레이션 생성 & 적용
npx prisma studio                # DB GUI
```

---

## 5. 성능 최적화

### Server Components 활용 상세

```typescript
// 클라이언트 번들에 포함되지 않는 무거운 연산
// Server Component에서만 사용
import { marked } from 'marked';         // 마크다운 파서 (번들에 미포함)
import { format } from 'date-fns';       // 날짜 포맷 (번들에 미포함)
import { highlight } from 'shiki';       // 코드 하이라이팅 (번들에 미포함)

export default async function ArticlePage({ params }: { params: { id: string } }) {
  const article = await db.article.findUnique({ where: { id: params.id } });

  // 서버에서 마크다운 변환 (클라이언트에 HTML만 전송)
  const htmlContent = marked(article.markdown);
  const formattedDate = format(article.createdAt, 'yyyy년 M월 d일');

  return (
    <article>
      <time>{formattedDate}</time>
      <div dangerouslySetInnerHTML={{ __html: htmlContent }} />
      {/* 인터랙션이 필요한 부분만 Client Component */}
      <CommentSection articleId={article.id} />
    </article>
  );
}
```

### 스트리밍 / Suspense 상세

#### loading.tsx 활용

```typescript
// loading.tsx는 해당 라우트 세그먼트 전체의 로딩 상태
// 자동으로 Suspense boundary로 감싸짐

// app/(dashboard)/dashboard/loading.tsx
export default function Loading() {
  return <DashboardSkeleton />;
}

// 위 코드는 아래와 동일하게 동작:
// <Suspense fallback={<DashboardSkeleton />}>
//   <DashboardPage />
// </Suspense>
```

#### Suspense 경계 설계

```typescript
// 느린 데이터와 빠른 데이터를 분리하여 점진적 렌더링
export default async function DashboardPage() {
  // 빠른 데이터는 즉시 표시
  const user = await getUser(); // 빠름 (캐시됨)

  return (
    <div>
      <h1>환영합니다, {user.name}</h1>

      {/* 느린 데이터는 Suspense로 분리 */}
      <div className="grid grid-cols-3 gap-4">
        <Suspense fallback={<StatCardSkeleton />}>
          <RevenueCard />  {/* 각각 독립적으로 스트리밍 */}
        </Suspense>
        <Suspense fallback={<StatCardSkeleton />}>
          <UsersCard />
        </Suspense>
        <Suspense fallback={<StatCardSkeleton />}>
          <OrdersCard />
        </Suspense>
      </div>

      {/* 매우 느린 데이터 */}
      <Suspense fallback={<AnalyticsSkeleton />}>
        <AnalyticsChart /> {/* 복잡한 쿼리, 마지막에 표시 */}
      </Suspense>
    </div>
  );
}

// 각 컴포넌트는 독립적인 async Server Component
async function RevenueCard() {
  const revenue = await getRevenue(); // 느린 외부 API
  return <StatCard title="매출" value={revenue} />;
}
```

### 이미지 최적화 상세

```typescript
import Image from 'next/image';

// 고정 크기 이미지 (width/height 필수)
<Image
  src="/images/hero.jpg"
  alt="히어로 이미지"
  width={1200}
  height={600}
  priority               // LCP 이미지에 필수 (lazy loading 비활성화)
  quality={85}            // 품질 (기본 75)
  placeholder="blur"      // 로딩 중 블러 효과
  blurDataURL="data:image/..."  // 로컬 이미지는 자동 생성
/>

// 반응형 이미지 (fill 모드)
<div className="relative aspect-video">  {/* 부모에 position: relative 필수 */}
  <Image
    src="/images/banner.jpg"
    alt="배너"
    fill                  // 부모 크기에 맞춤
    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
    className="object-cover"
    priority
  />
</div>

// 외부 이미지 (remotePatterns 설정 필수)
<Image
  src="https://cdn.example.com/photo.jpg"
  alt="외부 이미지"
  width={400}
  height={300}
  sizes="(max-width: 768px) 100vw, 400px"
/>
```

```javascript
// next.config.js - remotePatterns 설정
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'cdn.example.com',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: '*.amazonaws.com',
      },
    ],
    // 이미지 포맷 설정
    formats: ['image/avif', 'image/webp'],
    // 디바이스 크기 (sizes 속성에서 사용)
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  },
};
```

### 폰트 최적화

```typescript
// app/layout.tsx
import { Inter, Noto_Sans_KR } from 'next/font/google';
import localFont from 'next/font/local';

// Google 폰트 (자동 최적화 + self-hosting)
const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

// 한국어 폰트
const notoSansKr = Noto_Sans_KR({
  subsets: ['latin'],
  weight: ['400', '500', '700'],
  display: 'swap',
  variable: '--font-noto-sans-kr',
  preload: false,            // 한국어는 서브셋이 크므로 preload 비활성화 고려
});

// 로컬 폰트
const pretendard = localFont({
  src: [
    { path: '../public/fonts/Pretendard-Regular.woff2', weight: '400' },
    { path: '../public/fonts/Pretendard-Medium.woff2', weight: '500' },
    { path: '../public/fonts/Pretendard-Bold.woff2', weight: '700' },
  ],
  variable: '--font-pretendard',
  display: 'swap',
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className={`${inter.variable} ${notoSansKr.variable}`}>
      <body className="font-sans">{children}</body>
    </html>
  );
}
```

```css
/* tailwind.config.ts에서 CSS 변수 연결 */
/* globals.css 또는 tailwind.config.ts */
```

```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss';

const config: Config = {
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-inter)', 'var(--font-noto-sans-kr)', 'sans-serif'],
      },
    },
  },
};
```

### ISR / SSG / 캐싱 상세

#### generateStaticParams

```typescript
// 정적 생성할 페이지 목록 지정
// app/posts/[id]/page.tsx
export async function generateStaticParams() {
  const posts = await db.post.findMany({
    select: { id: true },
    where: { published: true },
    take: 100,                    // 가장 인기 있는 100개만 사전 생성
  });

  return posts.map((post) => ({
    id: post.id,
  }));
}

// 목록에 없는 경로 접근 시:
// dynamicParams = true (기본값): 요청 시 생성 후 캐시
// dynamicParams = false: 404 반환
export const dynamicParams = true;

export default async function PostPage({ params }: { params: { id: string } }) {
  const post = await getPost(params.id);
  if (!post) notFound();
  return <PostContent post={post} />;
}
```

#### 온디맨드 재검증

```typescript
// 경로 기반 재검증
'use server';
import { revalidatePath } from 'next/cache';

export async function updatePost(id: string, formData: FormData) {
  await db.post.update({ where: { id }, data: { /* ... */ } });

  revalidatePath('/posts');           // 목록 페이지 재검증
  revalidatePath(`/posts/${id}`);     // 상세 페이지 재검증
  revalidatePath('/posts', 'layout'); // layout 포함 재검증
}

// 태그 기반 재검증
import { revalidateTag } from 'next/cache';

export async function updateProduct(id: string) {
  await db.product.update({ where: { id }, data: { /* ... */ } });

  revalidateTag('products');          // 'products' 태그가 붙은 모든 fetch 재검증
  revalidateTag(`product-${id}`);
}
```

#### unstable_cache 활용

```typescript
import { unstable_cache } from 'next/cache';
import { db } from '@/lib/db';

// DB 쿼리 캐싱
const getCachedUser = unstable_cache(
  async (userId: string) => {
    return db.user.findUnique({
      where: { id: userId },
      include: { posts: true },
    });
  },
  ['user'],                          // 캐시 키 프리픽스
  {
    tags: ['user'],                  // 재검증 태그
    revalidate: 3600,                // 1시간 (초 단위)
  }
);

// React cache()로 요청 단위 중복 제거
import { cache } from 'react';

const getUser = cache(async (userId: string) => {
  return db.user.findUnique({ where: { id: userId } });
});

// 같은 렌더 트리에서 여러 번 호출해도 실제 쿼리는 1번만 실행
// layout.tsx: const user = await getUser(id);
// page.tsx:   const user = await getUser(id); // 캐시에서 반환
```

#### 캐싱 전략 결정 트리

```
데이터가 변경되나?
├── 거의 안 변함 → generateStaticParams + revalidate: 3600 (ISR)
├── 자주 변함 → cache: 'no-store' 또는 revalidate: 0
├── 사용자별 다름 → cache: 'no-store' (cookies/headers 사용 시 자동)
└── 특정 이벤트에 변함 → tags + revalidateTag (온디맨드)
```

### 번들 최적화

```typescript
// next/dynamic으로 지연 로드 (코드 분할)
import dynamic from 'next/dynamic';

// 무거운 컴포넌트 지연 로드
const HeavyChart = dynamic(() => import('@/components/chart'), {
  loading: () => <ChartSkeleton />,
  ssr: false,     // 서버 렌더링 불필요 시 (브라우저 API 사용 등)
});

// 조건부 렌더링과 함께
const AdminPanel = dynamic(() => import('@/components/admin-panel'));

export default function Dashboard({ isAdmin }: { isAdmin: boolean }) {
  return (
    <div>
      <MainContent />
      {isAdmin && <AdminPanel />}  {/* 관리자만 번들 로드 */}
    </div>
  );
}

// barrel file 문제
// [나쁨] components/index.ts에서 모든 컴포넌트 re-export
// import { Button } from '@/components'; // 모든 컴포넌트가 번들에 포함될 수 있음

// [좋음] 직접 import
// import { Button } from '@/components/ui/button';
```

```javascript
// @next/bundle-analyzer 설정
// next.config.js
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
});

module.exports = withBundleAnalyzer(nextConfig);

// 실행: ANALYZE=true npm run build
```

### Core Web Vitals 최적화

```
LCP (Largest Contentful Paint) 최적화:
- 히어로 이미지에 priority 속성 추가
- 폰트에 display: 'swap' 설정
- Server Component로 빠른 초기 렌더링
- <link rel="preload"> 중요 리소스

INP (Interaction to Next Paint) 최적화:
- useTransition으로 비긴급 업데이트 분리
- startTransition으로 무거운 상태 업데이트 래핑
- 이벤트 핸들러 내 무거운 연산 최소화
- React.memo()로 불필요한 리렌더링 방지

CLS (Cumulative Layout Shift) 최적화:
- 이미지에 width/height 또는 aspect-ratio 명시
- 폰트 로딩 시 size-adjust 또는 font-display: swap
- 동적 콘텐츠에 min-height 설정
- loading.tsx / Skeleton으로 레이아웃 안정화
```

### Edge Runtime vs Node.js Runtime

```typescript
// Edge Runtime 선택 기준
// - 낮은 지연 시간 필요 (CDN 엣지에서 실행)
// - 경량 연산 (인증 확인, 리디렉트, A/B 테스트)
// - Node.js API 불필요

// Middleware는 항상 Edge Runtime
// middleware.ts (Edge Runtime 자동)

// Route Handler에서 Edge Runtime 지정
export const runtime = 'edge';

export async function GET() {
  return new Response('Hello from Edge');
}

// Node.js Runtime 선택 기준
// - DB 직접 연결 (Prisma, pg 등)
// - 파일 시스템 접근 (fs)
// - Node.js 전용 라이브러리 (sharp, bcrypt 등)
// - 무거운 연산

// Page/Layout에서 Node.js Runtime 명시 (기본값)
export const runtime = 'nodejs';
```

---

## 6. 주의사항 / Gotchas

### "use client" 전파 문제

```typescript
// [문제] "use client" 파일에서 import한 모든 모듈이 클라이언트 번들에 포함됨

// heavy-utils.ts (서버 전용 의도)
import { parse } from 'some-huge-library'; // 500KB
export function processData(data: string) { return parse(data); }

// client-component.tsx
'use client';
import { processData } from '@/lib/heavy-utils'; // 500KB가 클라이언트 번들에 포함!

// [해결] 서버 전용 로직은 Server Component에서 처리 후 결과만 props로 전달
// page.tsx (Server Component)
import { processData } from '@/lib/heavy-utils'; // 서버에서만 사용

export default async function Page() {
  const result = processData(rawData); // 서버에서 처리
  return <ClientComponent result={result} />; // 결과만 전달
}
```

### Server Component에서 hooks 사용 불가

```typescript
// [에러] Server Component에서 useState 사용
export default function Page() {
  const [count, setCount] = useState(0); // Error!
  return <div>{count}</div>;
}

// [해결] hooks가 필요한 부분만 Client Component로 분리
export default function Page() {
  return (
    <div>
      <h1>서버에서 렌더링된 제목</h1>
      <Counter />  {/* Client Component */}
    </div>
  );
}
```

### searchParams/cookies()/headers() 동적 렌더링 전환

```typescript
// 이 함수들을 사용하면 해당 페이지가 동적 렌더링으로 전환됨
// (빌드 시 정적 생성 불가)

// cookies() → 동적 렌더링
import { cookies } from 'next/headers';
export default async function Page() {
  const theme = cookies().get('theme'); // 정적 생성 불가
}

// searchParams → 동적 렌더링
export default function Page({ searchParams }: { searchParams: { q: string } }) {
  // searchParams를 읽는 순간 동적 렌더링
}

// [해결] 동적 부분만 Client Component로 분리
export default function Page() {
  return (
    <div>
      <StaticContent />              {/* 정적 렌더링 */}
      <Suspense fallback={<Skeleton />}>
        <DynamicSection />           {/* 동적 부분만 분리 */}
      </Suspense>
    </div>
  );
}
```

### Layout은 리렌더링 안 됨

```typescript
// [문제] Layout은 네비게이션 시 리렌더링되지 않음
// URL이 /posts/1 → /posts/2로 변해도 Layout은 유지됨

// app/posts/layout.tsx
export default function PostLayout({ children }: { children: React.ReactNode }) {
  // 이 컴포넌트는 /posts/1 → /posts/2 이동 시 리렌더링 안 됨
  return <div>{children}</div>;
}

// [해결] URL 변화 감지가 필요하면 Client Component에서 usePathname 사용
'use client';
import { usePathname } from 'next/navigation';

export function Breadcrumb() {
  const pathname = usePathname(); // URL 변화 시마다 업데이트됨
  return <nav>{pathname}</nav>;
}

// 또는 template.tsx 사용 (매 네비게이션마다 리마운트)
// app/posts/template.tsx
export default function PostTemplate({ children }: { children: React.ReactNode }) {
  // 매번 새로 마운트됨
  return <div>{children}</div>;
}
```

### redirect()는 try/catch 내 호출 금지

```typescript
// [에러] redirect()는 내부적으로 에러를 throw하므로 catch됨
export default async function Page() {
  try {
    const data = await fetchData();
    if (!data) {
      redirect('/not-found'); // catch에 잡힘!
    }
  } catch (error) {
    // redirect의 throw가 여기서 잡힘 → 리다이렉트 안 됨
  }
}

// [해결] try/catch 밖에서 redirect 호출
export default async function Page() {
  let data;
  try {
    data = await fetchData();
  } catch (error) {
    // fetch 에러만 처리
  }

  if (!data) {
    redirect('/not-found'); // try/catch 밖
  }

  return <Content data={data} />;
}
```

### 환경변수 변경 후 서버 재시작 필수

```
.env.local 수정 후 반드시 dev 서버 재시작
핫 리로드 대상이 아님 (코드 변경과 달리 자동 반영 안 됨)
```

### fetch 캐싱 기본값 변경

```typescript
// Next.js 14: fetch 기본값 = force-cache (캐시됨)
// Next.js 15: fetch 기본값 = no-store (캐시 안 됨)

// 명시적으로 캐싱 옵션 지정 권장 (버전 독립적)
fetch(url, { cache: 'force-cache' });        // 명시적 캐시
fetch(url, { next: { revalidate: 3600 } });  // 시간 기반 재검증
fetch(url, { cache: 'no-store' });           // 캐시 없음
```

### Middleware는 Edge Runtime

```typescript
// middleware.ts는 Edge Runtime에서 실행됨
// Node.js 전용 API 사용 불가

// [에러]
import fs from 'fs';          // 사용 불가
import { PrismaClient } from '@prisma/client'; // 사용 불가 (일반적으로)
import bcrypt from 'bcrypt';   // 사용 불가 (native module)

// [허용]
import { NextResponse } from 'next/server'; // Web API 사용
// crypto, TextEncoder/TextDecoder, URL 등 Web 표준 API는 사용 가능
```

### 서버/클라이언트 컴포넌트 경계 직렬화 제한

```typescript
// Server Component에서 Client Component로 전달할 수 있는 props:
// - 직렬화 가능한 값만 가능 (JSON.stringify 가능한 값)
// - string, number, boolean, null, array, plain object, Date
// - 함수, Class 인스턴스, Map, Set 등은 전달 불가

// [에러]
export default function Page() {
  const handleClick = () => console.log('clicked');
  return <ClientButton onClick={handleClick} />;  // 함수 전달 불가!
}

// [해결] Client Component 내부에서 함수 정의
// 또는 Server Action을 prop으로 전달 (Server Action은 직렬화 가능)
import { deletePost } from '@/actions/post-actions';

export default function Page() {
  return <DeleteButton action={deletePost} />; // Server Action은 전달 가능
}
```

### next/navigation vs next/router

```typescript
// App Router: next/navigation 사용
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { redirect, notFound } from 'next/navigation';

// Pages Router (구버전): next/router 사용
// import { useRouter } from 'next/router'; // App Router에서 사용 금지!

// 혼동하면 빌드 에러 또는 런타임 에러 발생
```

### Server Action에서의 revalidate 타이밍

```typescript
// revalidatePath/revalidateTag는 Server Action 내에서 호출 시
// 현재 요청이 아닌 다음 요청에서 효과 발생

'use server';
export async function updatePost(id: string) {
  await db.post.update({ ... });
  revalidatePath('/posts');
  // 이 응답에서는 아직 이전 캐시를 볼 수 있음
  // 다음 네비게이션/요청에서 새 데이터 표시
}
```

### generateStaticParams + dynamic 조합

```typescript
// dynamic = "error": generateStaticParams에 없는 경로 접근 시 에러
export const dynamic = 'error';
export async function generateStaticParams() {
  return [{ id: '1' }, { id: '2' }];
}
// /posts/3 접근 → 빌드 에러 또는 404

// dynamic = "force-dynamic": 항상 동적 렌더링
export const dynamic = 'force-dynamic';
// generateStaticParams가 있어도 무시됨

// dynamic = "force-static": 항상 정적 렌더링 시도
export const dynamic = 'force-static';
// cookies(), headers() 등은 빈 값 반환
```

### Turbopack vs Webpack 차이

```
Turbopack (next dev --turbo):
- 빠른 HMR (증분 컴파일)
- 일부 Webpack 플러그인 미지원
- next.config.js의 webpack() 설정 무시됨
- 개발 환경에서만 사용 (빌드는 Webpack)

Webpack:
- 모든 플러그인/로더 지원
- next.config.js webpack() 설정 적용
- 빌드 + 개발 모두 사용 가능
- 상대적으로 느린 HMR
```