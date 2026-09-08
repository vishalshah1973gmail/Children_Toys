import { type FormEvent, useEffect, useState } from 'react'

import { adminApi } from '../../api/admin'
import { catalogApi } from '../../api/catalog'
import { toApiError } from '../../api/client'
import ErrorBanner from '../../components/ErrorBanner'
import Spinner from '../../components/Spinner'
import type { Category } from '../../types'

/** Create, rename and delete categories. */
export default function AdminCategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [editing, setEditing] = useState<Category | null>(null)

  async function load() {
    try {
      setCategories(await catalogApi.categories())
    } catch (caught) {
      setError(toApiError(caught).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      if (editing) {
        await adminApi.updateCategory(editing.id, { name, description })
      } else {
        await adminApi.createCategory({ name, description })
      }
      setName('')
      setDescription('')
      setEditing(null)
      await load()
    } catch (caught) {
      setError(toApiError(caught).message)
    }
  }

  async function handleDelete(category: Category) {
    setError(null)
    try {
      await adminApi.deleteCategory(category.id)
      await load()
    } catch (caught) {
      setError(toApiError(caught).message)
    }
  }

  if (loading) return <Spinner />

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <section>
        <ErrorBanner message={error} onDismiss={() => setError(null)} />
        <div className="card overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-ink-800/10 text-xs uppercase tracking-wide text-ink-700">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Slug</th>
                <th className="px-4 py-3 text-right">Products</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-800/5">
              {categories.map((category) => (
                <tr key={category.id}>
                  <td className="px-4 py-3 font-medium">{category.name}</td>
                  <td className="px-4 py-3 text-ink-700">{category.slug}</td>
                  <td className="px-4 py-3 text-right">{category.product_count}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      className="text-brand-700 hover:underline"
                      onClick={() => {
                        setEditing(category)
                        setName(category.name)
                        setDescription(category.description ?? '')
                      }}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="ml-3 text-red-700 hover:underline disabled:opacity-40"
                      disabled={category.product_count > 0}
                      title={
                        category.product_count > 0
                          ? 'Move or delete its products first'
                          : 'Delete category'
                      }
                      onClick={() => void handleDelete(category)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <form onSubmit={handleSubmit} className="card h-fit space-y-4 p-5">
        <h2 className="font-display text-lg text-ink-900">
          {editing ? `Edit ${editing.name}` : 'New category'}
        </h2>

        <div>
          <label className="label" htmlFor="cat-name">
            Name
          </label>
          <input
            id="cat-name"
            className="input"
            required
            minLength={2}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </div>

        <div>
          <label className="label" htmlFor="cat-description">
            Description
          </label>
          <textarea
            id="cat-description"
            className="input h-24"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </div>

        <div className="flex gap-2">
          <button type="submit" className="btn-primary flex-1">
            {editing ? 'Save changes' : 'Create category'}
          </button>
          {editing && (
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setEditing(null)
                setName('')
                setDescription('')
              }}
            >
              Cancel
            </button>
          )}
        </div>
      </form>
    </div>
  )
}
