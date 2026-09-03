const routes = [
	{
		name: "HRRequestListView",
		path: "/hr-requests",
		component: () => import("@/views/hr_request/List.vue"),
	},
	{
		name: "HRRequestFormView",
		path: "/hr-requests/new",
		component: () => import("@/views/hr_request/Form.vue"),
	},
	{
		name: "HRRequestDetailView",
		path: "/hr-requests/:id",
		props: true,
		component: () => import("@/views/hr_request/Form.vue"),
	},
]

export default routes
